"""
Exchange Rate Management API Views

This module provides administrative API endpoints for managing
dynamic exchange rates, viewing rate history, and configuring
rate sources.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes

from .models import ExchangeRate, Currency
from .quidax_exchange_service import QuidaxExchangeRateService
from .serializers import ExchangeRateSerializer, ExchangeRateUpdateSerializer
import logging

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['Exchange Rate Management'],
    summary='Get current exchange rate',
    description='Get the current exchange rate for a specific currency pair with amount-based pricing',
    parameters=[
        OpenApiParameter('from_currency', OpenApiTypes.STR, description='Source currency code'),
        OpenApiParameter('to_currency', OpenApiTypes.STR, description='Target currency code'), 
        OpenApiParameter('amount', OpenApiTypes.NUMBER, description='Amount for tiered pricing (optional)')
    ]
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_exchange_rate(request):
    """
    Get current exchange rate for a currency pair
    """
    from_currency = request.query_params.get('from_currency', '').upper()
    to_currency = request.query_params.get('to_currency', '').upper()
    amount_str = request.query_params.get('amount')
    
    if not from_currency or not to_currency:
        return Response({
            'error': 'Both from_currency and to_currency parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    amount = None
    if amount_str:
        try:
            amount = Decimal(amount_str)
        except (InvalidOperation, ValueError):
            return Response({
                'error': 'Invalid amount format'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        rate_info = QuidaxExchangeRateService.get_exchange_rate(
            from_currency=from_currency,
            to_currency=to_currency,
            amount=amount
        )
        
        if 'error' in rate_info:
            return Response(rate_info, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'from_currency': from_currency,
            'to_currency': to_currency,
            'amount': str(amount) if amount else None,
            'exchange_rate': rate_info['rate'],
            'rate_source': rate_info.get('source', 'unknown'),
            'timestamp': rate_info.get('timestamp'),
            'rate_details': rate_info
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting exchange rate: {e}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Exchange Rate Management'],
    summary='Calculate currency conversion',
    description='Calculate complete currency conversion with detailed breakdown',
    parameters=[
        OpenApiParameter('from_currency', OpenApiTypes.STR, description='Source currency code'),
        OpenApiParameter('to_currency', OpenApiTypes.STR, description='Target currency code'),
        OpenApiParameter('amount', OpenApiTypes.NUMBER, description='Amount to convert')
    ]
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def calculate_conversion(request):
    """
    Calculate currency conversion with full details
    """
    from_currency = request.query_params.get('from_currency', '').upper()
    to_currency = request.query_params.get('to_currency', '').upper() 
    amount_str = request.query_params.get('amount')
    
    if not all([from_currency, to_currency, amount_str]):
        return Response({
            'error': 'from_currency, to_currency, and amount parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        return Response({
            'error': 'Invalid amount format'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        conversion_result = QuidaxExchangeRateService.calculate_conversion(
            from_currency=from_currency,
            to_currency=to_currency,
            amount=amount
        )
        
        if 'error' in conversion_result:
            return Response(conversion_result, status=status.HTTP_404_NOT_FOUND)
        
        return Response(conversion_result, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error calculating conversion: {e}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Exchange Rate Management'],
    summary='Get supported currency pairs',
    description='Get list of all supported currency pairs for exchange'
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_supported_pairs(request):
    """
    Get list of supported currency pairs
    """
    try:
        pairs = QuidaxExchangeRateService.get_supported_currency_pairs()
        return Response({
            'supported_pairs': pairs,
            'total_pairs': len(pairs)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting supported pairs: {e}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExchangeRateManagementView(APIView):
    """
    Administrative view for managing exchange rates
    """
    permission_classes = [permissions.IsAdminUser]
    
    @extend_schema(
        tags=['Exchange Rate Management'],
        summary='Update exchange rate',
        description='Update or create an exchange rate for a currency pair (Admin only)',
        request=ExchangeRateUpdateSerializer
    )
    def post(self, request):
        """Update/create exchange rate"""
        serializer = ExchangeRateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        try:
            exchange_rate = QuidaxExchangeRateService.update_exchange_rate(
                from_currency=data['currency_from'],
                to_currency=data['currency_to'],
                rate=data['rate'],
                low_amount=data.get('low_amount'),
                low_amount_limit=data.get('low_amount_limit')
            )
            
            return Response({
                'message': 'Exchange rate updated successfully',
                'exchange_rate': {
                    'from_currency': exchange_rate.currency_from,
                    'to_currency': exchange_rate.currency_to,
                    'rate': str(exchange_rate.rate),
                    'low_amount': str(exchange_rate.low_amount) if exchange_rate.low_amount else None,
                    'low_amount_limit': str(exchange_rate.low_amount_limit) if exchange_rate.low_amount_limit else None,
                    'created_at': exchange_rate.created_at
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error updating exchange rate: {e}")
            return Response({
                'error': 'Failed to update exchange rate'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Exchange Rate Management'],
    summary='List all exchange rates',
    description='Get list of all configured exchange rates (Admin only)'
)
class ExchangeRateListView(generics.ListAPIView):
    """List all configured exchange rates"""
    
    serializer_class = ExchangeRateSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return ExchangeRate.objects.all().order_by('-created_at')


@extend_schema(
    tags=['Exchange Rate Management'],
    summary='Get exchange rate history',
    description='Get historical exchange rates for a currency pair',
    parameters=[
        OpenApiParameter('from_currency', OpenApiTypes.STR, description='Source currency code'),
        OpenApiParameter('to_currency', OpenApiTypes.STR, description='Target currency code'),
        OpenApiParameter('days', OpenApiTypes.INT, description='Number of days to look back (default: 7)')
    ]
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_rate_history(request):
    """
    Get historical exchange rates for a currency pair
    """
    from_currency = request.query_params.get('from_currency', '').upper()
    to_currency = request.query_params.get('to_currency', '').upper()
    days = int(request.query_params.get('days', 7))
    
    if not from_currency or not to_currency:
        return Response({
            'error': 'Both from_currency and to_currency parameters are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    from datetime import timedelta
    cutoff_date = timezone.now() - timedelta(days=days)
    
    try:
        rates = ExchangeRate.objects.filter(
            currency_from=from_currency,
            currency_to=to_currency,
            created_at__gte=cutoff_date
        ).order_by('-created_at')
        
        rate_history = []
        for rate in rates:
            rate_history.append({
                'rate': str(rate.rate),
                'low_amount': str(rate.low_amount) if rate.low_amount else None,
                'low_amount_limit': str(rate.low_amount_limit) if rate.low_amount_limit else None,
                'created_at': rate.created_at
            })
        
        return Response({
            'from_currency': from_currency,
            'to_currency': to_currency,
            'history_days': days,
            'rate_history': rate_history,
            'total_records': len(rate_history)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting rate history: {e}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Exchange Rate Management'],
    summary='Refresh rates from external APIs',
    description='Force refresh of all exchange rates from external APIs (Admin only)'
)
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def refresh_rates_from_apis(request):
    """
    Force refresh of exchange rates from external APIs
    """
    try:
        from django.core.cache import cache
        
        # Currency pairs to refresh
        pairs_to_refresh = [
            ('NGN', 'USD'), ('USD', 'NGN'),
            ('UGX', 'NGN'), ('NGN', 'UGX'),
            ('USD', 'UGX'), ('UGX', 'USD')
        ]
        
        refreshed_rates = []
        failed_pairs = []
        
        for from_currency, to_currency in pairs_to_refresh:
            # Clear cache for this pair
            cache_key = f"quidax_rate_{from_currency}_{to_currency}"
            cache.delete(cache_key)
            
            # Try to fetch fresh rate from Quidax API
            api_rate = QuidaxExchangeRateService._fetch_quidax_rate(from_currency, to_currency)
            
            if api_rate and 'error' not in api_rate:
                # Update database with fresh rate
                rate_obj = QuidaxExchangeRateService.update_exchange_rate(
                    from_currency=from_currency,
                    to_currency=to_currency,
                    rate=Decimal(str(api_rate['rate']))
                )
                
                refreshed_rates.append({
                    'pair': f"{from_currency}_{to_currency}",
                    'rate': str(rate_obj.rate),
                    'source': api_rate['source'],
                    'updated_at': rate_obj.created_at
                })
            else:
                failed_pairs.append(f"{from_currency}_{to_currency}")
        
        return Response({
            'message': 'Rate refresh completed',
            'refreshed_pairs': len(refreshed_rates),
            'failed_pairs': len(failed_pairs),
            'refreshed_rates': refreshed_rates,
            'failed': failed_pairs
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error refreshing rates: {e}")
        return Response({
            'error': 'Failed to refresh rates'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Exchange Rate Management'],
    summary='Get rate service configuration',
    description='Get current configuration of the exchange rate service'
)
@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def get_rate_service_config(request):
    """
    Get exchange rate service configuration
    """
    try:
        config = {
            'cache_timeout': QuidaxExchangeRateService.CACHE_TIMEOUT,
            'fallback_cache_timeout': QuidaxExchangeRateService.FALLBACK_CACHE_TIMEOUT,
            'service_provider': 'quidax',
            'base_url': QuidaxExchangeRateService.BASE_URL,
            'api_configured': bool(QuidaxExchangeRateService.API_KEY),
            'sandbox_mode': QuidaxExchangeRateService.SANDBOX_MODE,
            'default_margins': QuidaxExchangeRateService.DEFAULT_MARGINS
        }
        
        return Response(config, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting service config: {e}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Quidax Integration'],
    summary='Get Quidax markets',
    description='Get all available markets from Quidax'
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_quidax_markets(request):
    """
    Get all available markets from Quidax
    """
    try:
        markets_data = QuidaxExchangeRateService.get_quidax_markets()
        
        if 'error' in markets_data:
            return Response(markets_data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(markets_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting Quidax markets: {e}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    tags=['Quidax Integration'],
    summary='Get market ticker',
    description='Get ticker data for a specific Quidax market',
    parameters=[
        OpenApiParameter('market', OpenApiTypes.STR, description='Market symbol (e.g., BTCNGN, USDTNGN)')
    ]
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_market_ticker(request):
    """
    Get ticker data for a specific market
    """
    market = request.query_params.get('market', '').upper()
    
    if not market:
        return Response({
            'error': 'Market parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        ticker_data = QuidaxExchangeRateService.get_market_ticker(market)
        
        if 'error' in ticker_data:
            return Response(ticker_data, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(ticker_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting market ticker: {e}")
        return Response({
            'error': 'Internal server error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
