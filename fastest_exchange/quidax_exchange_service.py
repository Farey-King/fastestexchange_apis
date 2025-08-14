"""
Quidax Exchange Rate Service

This service handles exchange rate calculations using Quidax API,
rate caching, and fallback mechanisms.

Based on Quidax API documentation: https://docs.quidax.ng/docs/getting-started
"""
import requests
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from .models import ExchangeRate, Currency
import logging

logger = logging.getLogger(__name__)


class QuidaxExchangeRateService:
    """
    Quidax-based service for managing dynamic exchange rates
    """
    
    # Cache timeouts in seconds
    CACHE_TIMEOUT = 300  # 5 minutes for live rates
    FALLBACK_CACHE_TIMEOUT = 3600  # 1 hour for fallback rates
    
    # Quidax API configuration
    BASE_URL = getattr(settings, 'QUIDAX_BASE_URL', 'https://www.quidax.com/api/v1')
    API_KEY = getattr(settings, 'QUIDAX_API_KEY', '')
    SECRET_KEY = getattr(settings, 'QUIDAX_SECRET_KEY', '')
    SANDBOX_MODE = getattr(settings, 'QUIDAX_SANDBOX_MODE', True)
    
    # Default margins/spreads per currency pair (in percentage)
    DEFAULT_MARGINS = {
        'NGN_USD': {'buy': 0.02, 'sell': 0.02},  # 2% margin
        'USD_NGN': {'buy': 0.02, 'sell': 0.02},
        'UGX_NGN': {'buy': 0.03, 'sell': 0.03},  # 3% margin
        'NGN_UGX': {'buy': 0.03, 'sell': 0.03},
        'USD_UGX': {'buy': 0.025, 'sell': 0.025}, # 2.5% margin
        'UGX_USD': {'buy': 0.025, 'sell': 0.025},
    }
    
    @classmethod
    def _get_headers(cls) -> Dict[str, str]:
        """Get headers for Quidax API requests"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if cls.API_KEY:
            headers['Authorization'] = f'Bearer {cls.API_KEY}'
            
        return headers
    
    @classmethod
    def get_exchange_rate(cls, from_currency: str, to_currency: str, amount: Optional[Decimal] = None) -> Dict:
        """
        Get the current exchange rate for a currency pair from Quidax
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code  
            amount: Optional amount to consider for tiered pricing
            
        Returns:
            Dict containing rate info or error
        """
        if from_currency == to_currency:
            return {'error': 'Cannot exchange the same currency'}
            
        # Try to get cached rate first
        cache_key = f"quidax_rate_{from_currency}_{to_currency}"
        cached_rate = cache.get(cache_key)
        
        if cached_rate:
            logger.info(f"Using cached Quidax rate for {from_currency}->{to_currency}")
            return cls._apply_amount_based_pricing(cached_rate, amount)
        
        # Try to get rate from Quidax API
        quidax_rate = cls._fetch_quidax_rate(from_currency, to_currency)
        if quidax_rate and 'error' not in quidax_rate:
            # Cache the Quidax rate
            cache.set(cache_key, quidax_rate, cls.CACHE_TIMEOUT)
            return cls._apply_amount_based_pricing(quidax_rate, amount)
        
        # Try to get rate from database as fallback
        db_rate = cls._get_db_rate(from_currency, to_currency)
        if db_rate and 'error' not in db_rate:
            # Cache the database rate
            cache.set(cache_key, db_rate, cls.CACHE_TIMEOUT)
            return cls._apply_amount_based_pricing(db_rate, amount)
        
        # Use hardcoded fallback rates
        fallback_rate = cls._get_fallback_rate(from_currency, to_currency)
        if fallback_rate:
            cache.set(cache_key, fallback_rate, cls.FALLBACK_CACHE_TIMEOUT)
            return cls._apply_amount_based_pricing(fallback_rate, amount)
        
        return {
            'error': f'Exchange rate not available for {from_currency} to {to_currency}'
        }
    
    @classmethod
    def _fetch_quidax_rate(cls, from_currency: str, to_currency: str) -> Optional[Dict]:
        """
        Fetch exchange rate from Quidax API
        
        Based on Quidax API documentation for getting market data
        """
        try:
            # Quidax uses market pairs format like BTCNGN, USDTNGN etc.
            # For fiat-to-fiat, we need to handle differently
            
            if from_currency == 'USD' and to_currency == 'NGN':
                # Get USD/NGN rate from Quidax USDT/NGN market (approximation)
                market = 'USDTNGN'
            elif from_currency == 'NGN' and to_currency == 'USD':
                # Get NGN/USD rate (inverse of USD/NGN)
                market = 'USDTNGN'
            else:
                # For other currency pairs, we'll need to use fallback
                logger.info(f"Quidax doesn't directly support {from_currency}/{to_currency} pair")
                return None
            
            url = f"{cls.BASE_URL}/markets/{market}/tickers"
            
            response = requests.get(
                url,
                headers=cls._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'last_price' in data['data']:
                    rate = float(data['data']['last_price'])
                    
                    # If we're converting NGN to USD, we need the inverse
                    if from_currency == 'NGN' and to_currency == 'USD':
                        rate = 1 / rate
                    
                    return {
                        'rate': rate,
                        'source': 'quidax_api',
                        'timestamp': timezone.now().isoformat(),
                        'pair': f"{from_currency}_{to_currency}",
                        'market': market,
                        'raw_data': data['data']
                    }
                else:
                    logger.error(f"Unexpected Quidax API response format: {data}")
                    return None
            else:
                logger.error(f"Quidax API returned status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching rate from Quidax API: {e}")
            return None
    
    @classmethod
    def _get_db_rate(cls, from_currency: str, to_currency: str) -> Optional[Dict]:
        """
        Get exchange rate from database as fallback
        """
        try:
            # Find the most recent rate for this currency pair
            rate_obj = ExchangeRate.objects.filter(
                currency_from=from_currency,
                currency_to=to_currency
            ).order_by('-created_at').first()
            
            if not rate_obj:
                return None
            
            # Check if rate is too old (older than 1 hour)
            time_diff = timezone.now() - rate_obj.created_at
            if time_diff.total_seconds() > 3600:  # 1 hour
                logger.warning(f"Database rate for {from_currency}->{to_currency} is outdated")
                return None
            
            return {
                'rate': float(rate_obj.rate),
                'source': 'database_fallback',
                'timestamp': rate_obj.created_at.isoformat(),
                'pair': f"{from_currency}_{to_currency}"
            }
            
        except Exception as e:
            logger.error(f"Error fetching DB rate for {from_currency}->{to_currency}: {e}")
            return None
    
    @classmethod
    def _get_fallback_rate(cls, from_currency: str, to_currency: str) -> Optional[Dict]:
        """
        Get hardcoded fallback static rates
        """
        FALLBACK_RATES = {
            'NGN_USD': 1610,  # Divide NGN by 1610 to get USD
            'USD_NGN': 1550,  # Multiply USD by 1550 to get NGN
            'UGX_NGN': 2.35,  # Multiply UGX by 2.35 to get NGN
            'NGN_UGX': 2.27,  # Multiply NGN by 2.27 to get UGX
            'USD_UGX': 3700,  # Multiply USD by 3700 to get UGX  
            'UGX_USD': 3800,  # Divide UGX by 3800 to get USD
        }
        
        pair_key = f"{from_currency}_{to_currency}"
        
        if pair_key in FALLBACK_RATES:
            rate_value = FALLBACK_RATES[pair_key]
            
            # For division pairs (like NGN_USD, UGX_USD), rate is 1/value
            if pair_key in ['NGN_USD', 'UGX_USD']:
                final_rate = 1 / rate_value
            else:
                final_rate = rate_value
            
            return {
                'rate': final_rate,
                'source': 'fallback_static',
                'timestamp': timezone.now().isoformat(),
                'pair': pair_key,
                'raw_rate': rate_value
            }
        
        return None
    
    @classmethod
    def _apply_amount_based_pricing(cls, rate_info: Dict, amount: Optional[Decimal]) -> Dict:
        """
        Apply amount-based tiered pricing and margins
        """
        if not amount:
            return rate_info
        
        base_rate = rate_info['rate']
        pair = rate_info['pair']
        
        # Apply margins
        margin_config = cls.DEFAULT_MARGINS.get(pair, {'buy': 0.02, 'sell': 0.02})
        
        # For customer buying foreign currency (we sell), apply sell margin
        # For customer selling foreign currency (we buy), apply buy margin
        from_currency, to_currency = pair.split('_')
        
        if from_currency in ['NGN', 'UGX']:  # Customer selling local currency
            margin = margin_config['buy']
            adjusted_rate = base_rate * (1 - margin)  # Lower rate when we buy
        else:  # Customer buying local currency  
            margin = margin_config['sell']
            adjusted_rate = base_rate * (1 + margin)  # Higher rate when we sell
        
        # Apply volume-based discounts
        volume_multiplier = 1.0
        if amount >= Decimal('10000'):  # Large transactions get better rates
            volume_multiplier = 0.995  # 0.5% discount
        elif amount >= Decimal('5000'):  # Medium transactions
            volume_multiplier = 0.998  # 0.2% discount
        
        final_rate = adjusted_rate * volume_multiplier
        
        rate_info.update({
            'original_rate': base_rate,
            'margin_applied': margin,
            'volume_discount': 1 - volume_multiplier,
            'final_rate': final_rate,
            'rate': final_rate  # Override the rate with final calculated rate
        })
        
        return rate_info
    
    @classmethod
    def get_quidax_markets(cls) -> Dict:
        """
        Get all available markets from Quidax
        """
        try:
            url = f"{cls.BASE_URL}/markets"
            
            response = requests.get(
                url,
                headers=cls._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'markets': data.get('data', []),
                    'source': 'quidax_api',
                    'timestamp': timezone.now().isoformat()
                }
            else:
                logger.error(f"Failed to fetch Quidax markets: {response.status_code}")
                return {'error': 'Failed to fetch markets from Quidax'}
                
        except Exception as e:
            logger.error(f"Error fetching Quidax markets: {e}")
            return {'error': str(e)}
    
    @classmethod
    def get_market_ticker(cls, market: str) -> Dict:
        """
        Get ticker data for a specific market
        
        Args:
            market: Market symbol like 'BTCNGN', 'USDTNGN'
        """
        try:
            url = f"{cls.BASE_URL}/markets/{market}/tickers"
            
            response = requests.get(
                url,
                headers=cls._get_headers(),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'ticker': data.get('data', {}),
                    'market': market,
                    'source': 'quidax_api',
                    'timestamp': timezone.now().isoformat()
                }
            else:
                logger.error(f"Failed to fetch ticker for {market}: {response.status_code}")
                return {'error': f'Failed to fetch ticker for {market}'}
                
        except Exception as e:
            logger.error(f"Error fetching ticker for {market}: {e}")
            return {'error': str(e)}
    
    @classmethod
    def update_exchange_rate(cls, from_currency: str, to_currency: str, rate: Decimal, 
                           low_amount: Optional[Decimal] = None, 
                           low_amount_limit: Optional[Decimal] = None) -> ExchangeRate:
        """
        Update or create an exchange rate in the database
        """
        exchange_rate, created = ExchangeRate.objects.update_or_create(
            currency_from=from_currency,
            currency_to=to_currency,
            defaults={
                'rate': rate,
                'low_amount': low_amount,
                'low_amount_limit': low_amount_limit,
            }
        )
        
        # Clear cache for this currency pair
        cache_key = f"quidax_rate_{from_currency}_{to_currency}"
        cache.delete(cache_key)
        
        logger.info(f"{'Created' if created else 'Updated'} exchange rate: {from_currency}->{to_currency} @ {rate}")
        
        return exchange_rate
    
    @classmethod
    def get_supported_currency_pairs(cls) -> List[Dict[str, str]]:
        """
        Get list of supported currency pairs
        """
        # Get pairs from database
        db_pairs = list(ExchangeRate.objects.values_list('currency_from', 'currency_to'))
        
        # Add fallback pairs that we support
        fallback_pairs = [
            ('NGN', 'USD'), ('USD', 'NGN'),
            ('UGX', 'NGN'), ('NGN', 'UGX'),
            ('USD', 'UGX'), ('UGX', 'USD')
        ]
        
        all_pairs = list(set(db_pairs + fallback_pairs))
        return [{'from': pair[0], 'to': pair[1]} for pair in all_pairs]
    
    @classmethod
    def calculate_conversion(cls, from_currency: str, to_currency: str, amount: Decimal) -> Dict:
        """
        Calculate complete currency conversion with all details
        """
        rate_info = cls.get_exchange_rate(from_currency, to_currency, amount)
        
        if 'error' in rate_info:
            return rate_info
        
        conversion_rate = Decimal(str(rate_info['rate'])).quantize(
            Decimal('0.000001'), rounding=ROUND_HALF_UP
        )
        
        converted_amount = (amount * conversion_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return {
            'from_currency': from_currency,
            'to_currency': to_currency,
            'amount_sent': float(amount),
            'converted_amount': float(converted_amount),
            'exchange_rate': float(conversion_rate),
            'rate_info': rate_info,
            'calculation_time': timezone.now().isoformat(),
            'service_provider': 'quidax'
        }
