# Dynamic Exchange Rate Implementation for SwapEngine

This document provides comprehensive information about the dynamic exchange rate system implemented for the SwapEngine.

## Overview

The dynamic exchange rate system replaces static rates with intelligent rate management that:

- **Fetches live rates** from multiple third-party APIs
- **Caches rates** for performance optimization
- **Applies margins and volume discounts** for business profitability
- **Falls back to static rates** for reliability
- **Provides administrative controls** for rate management
- **Supports automatic updates** via cron jobs

## Architecture

### Components

1. **ExchangeRateService** - Core service handling rate calculations
2. **ExchangeRate Model** - Database storage for rates
3. **Exchange Rate Views** - API endpoints for management
4. **Management Command** - Automated rate updates
5. **SwapView Updates** - Integration with existing swap logic

### Data Flow

```
Client Request → SwapView → ExchangeRateService → Rate Sources (Cache/DB/APIs/Fallback) → Calculated Rate
```

## API Endpoints

### Public Endpoints (No Authentication Required)

#### Get Exchange Rate
```http
GET /api/exchange-rates/get/?from_currency=NGN&to_currency=USD&amount=1000
```

**Response:**
```json
{
    "from_currency": "NGN",
    "to_currency": "USD", 
    "amount": "1000",
    "exchange_rate": 0.000621,
    "rate_source": "fixer",
    "timestamp": "2024-08-13T10:30:00Z",
    "rate_details": {
        "rate": 0.000621,
        "source": "fixer",
        "original_rate": 0.000635,
        "margin_applied": 0.02,
        "volume_discount": 0.0,
        "final_rate": 0.000621
    }
}
```

#### Calculate Conversion
```http
GET /api/exchange-rates/convert/?from_currency=NGN&to_currency=USD&amount=50000
```

**Response:**
```json
{
    "from_currency": "NGN",
    "to_currency": "USD",
    "amount_sent": 50000.0,
    "converted_amount": 31.05,
    "exchange_rate": 0.000621,
    "rate_info": {
        "source": "fixer",
        "margin_applied": 0.02,
        "volume_discount": 0.002
    },
    "calculation_time": "2024-08-13T10:30:00Z"
}
```

#### Get Supported Currency Pairs
```http
GET /api/exchange-rates/pairs/
```

### Admin Endpoints (Admin Authentication Required)

#### Update Exchange Rate
```http
POST /api/admin/exchange-rates/update/
Content-Type: application/json

{
    "currency_from": "NGN",
    "currency_to": "USD", 
    "rate": "0.000620",
    "low_amount": "0.000615",
    "low_amount_limit": "1000000"
}
```

#### List All Exchange Rates
```http
GET /api/admin/exchange-rates/list/
```

#### Get Rate History
```http
GET /api/admin/exchange-rates/history/?from_currency=NGN&to_currency=USD&days=7
```

#### Refresh Rates from APIs
```http
POST /api/admin/exchange-rates/refresh/
```

#### Get Service Configuration
```http
GET /api/admin/exchange-rates/config/
```

## SwapView Integration

The SwapView now uses dynamic rates through the `calculate_swap` method:

```python
# Before (Static Rates)
EXCHANGE_RATES = {
    'NGN_TO_USD': 1610,  # Fixed rate
    'USD_TO_NGN': 1550,
}

# After (Dynamic Rates) 
conversion_result = ExchangeRateService.calculate_conversion(
    from_currency=from_currency,
    to_currency=to_currency, 
    amount=amount_decimal
)
```

### Enhanced Response

The SwapView response now includes additional rate information:

```json
{
    "message": "Swap created successfully. Awaiting payment.",
    "transaction_id": 123,
    "swap_details": {
        "from_currency": "NGN",
        "to_currency": "USD",
        "amount_sent": 50000,
        "amount_to_receive": 31.05,
        "exchange_rate": 0.000621,
        "rate_type": "NGN to USD - Live Market Rate (Fixer.io) (Margin: 2.0%) (Volume Discount: 0.2%)"
    },
    "status": "pending"
}
```

## Rate Sources and Fallback System

The system uses a hierarchical approach to get the best available rate:

### 1. Cache (Fastest)
- **Timeout:** 5 minutes for live rates
- **Storage:** Django cache (Redis recommended)
- **Usage:** First check for recently fetched rates

### 2. Database (Fast)
- **Freshness:** Rates older than 1 hour are considered stale
- **Features:** Supports tiered pricing with low_amount and low_amount_limit
- **Usage:** Admin-configured rates and recently updated API rates

### 3. External APIs (Live)
- **Fixer.io:** 100 requests/month (free tier)
- **ExchangeRate-API:** 1,500 requests/month (free tier)  
- **CurrencyAPI:** 300 requests/month (free tier)
- **Usage:** Live market rates when cache/DB is stale

### 4. Static Fallback (Reliable)
- **NGN ↔ USD:** Original rates (1610/1550)
- **UGX ↔ NGN:** Example rates (2.35/2.27)
- **USD ↔ UGX:** Added rates (3700/3800)
- **Usage:** When all other sources fail

## Margin and Volume Discounts

### Default Margins
```python
DEFAULT_MARGINS = {
    'NGN_USD': {'buy': 0.02, 'sell': 0.02},  # 2% margin
    'USD_NGN': {'buy': 0.02, 'sell': 0.02},
    'UGX_NGN': {'buy': 0.03, 'sell': 0.03},  # 3% margin
    'NGN_UGX': {'buy': 0.03, 'sell': 0.03},
    'USD_UGX': {'buy': 0.025, 'sell': 0.025}, # 2.5% margin
    'UGX_USD': {'buy': 0.025, 'sell': 0.025},
}
```

### Volume-Based Discounts
- **≥ $10,000 equivalent:** 0.5% discount
- **≥ $5,000 equivalent:** 0.2% discount
- **< $5,000 equivalent:** No discount

## Management Commands

### Update Exchange Rates
```bash
# Update all currency pairs
python manage.py update_exchange_rates

# Update specific pairs
python manage.py update_exchange_rates --currency-pairs NGN_USD USD_NGN

# Force refresh (ignore cache)
python manage.py update_exchange_rates --force-refresh

# Dry run (show what would be updated)
python manage.py update_exchange_rates --dry-run --verbose
```

### Cron Job Setup
Add to crontab for automatic updates:
```bash
# Every hour
0 * * * * /path/to/venv/bin/python /path/to/project/manage.py update_exchange_rates

# Every 30 minutes  
*/30 * * * * /path/to/venv/bin/python /path/to/project/manage.py update_exchange_rates
```

## Configuration

### Environment Variables
Add to your `.env` file:
```bash
# API Keys
FIXER_API_KEY=your_fixer_api_key_here
EXCHANGERATE_API_KEY=your_exchangerate_api_key_here
CURRENCY_API_KEY=your_currency_api_key_here

# Redis (optional, improves caching performance)
REDIS_URL=redis://localhost:6379/1
```

### Django Settings
```python
# Caching (recommended)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'loggers': {
        'fastest_exchange.exchange_rate_service': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## Benefits

### For Users
- **Real-time rates:** Always get current market rates
- **Better prices:** Volume discounts for large transactions
- **Transparency:** See rate source and breakdown
- **Reliability:** Multiple fallback options ensure service availability

### For Business
- **Profit margins:** Configurable margins on all transactions
- **Risk management:** Automatic rate updates reduce manual oversight
- **Analytics:** Rate history and source tracking
- **Scalability:** Supports high transaction volumes with caching

### For Administrators
- **Control:** Manual rate override capabilities
- **Monitoring:** Rate history and source configuration
- **Automation:** Scheduled rate updates via cron
- **Flexibility:** Easy addition of new currency pairs

## Monitoring and Maintenance

### Key Metrics to Monitor
- **Rate source distribution:** Percentage from cache/DB/APIs/fallback
- **API quotas:** Usage across different providers
- **Rate change frequency:** How often rates are updating
- **Failed rate fetches:** Monitor for API issues

### Maintenance Tasks
- **Weekly:** Review rate history for anomalies
- **Monthly:** Check API usage against quotas
- **Quarterly:** Review margin settings and profitability
- **As needed:** Add new currency pairs or API providers

## Troubleshooting

### Common Issues

#### Rates Not Updating
1. Check API keys in environment variables
2. Verify API quotas haven't been exceeded
3. Check cron job configuration
4. Review logs for rate fetch errors

#### Cache Issues
1. Restart Redis if using Redis cache
2. Clear cache manually: `python manage.py shell -c "from django.core.cache import cache; cache.clear()"`
3. Check cache configuration in settings

#### Fallback Rates Being Used
1. Update API keys
2. Check network connectivity
3. Verify API endpoints are accessible
4. Check rate service configuration

### Error Codes
- **404:** Currency pair not supported
- **500:** Rate calculation error (check logs)
- **429:** API rate limit exceeded
- **400:** Invalid request parameters

## Future Enhancements

### Planned Features
- **WebSocket rate streaming:** Real-time rate updates
- **Machine learning:** Predictive rate trends
- **Multi-provider aggregation:** Composite rates from multiple sources
- **Rate alerts:** Notifications for significant rate changes
- **A/B testing:** Different margin strategies for user segments

### API Provider Expansion
- **Alpha Vantage**
- **Open Exchange Rates**
- **CurrencyLayer**
- **XE.com API**

This dynamic exchange rate system provides a robust, scalable, and profitable foundation for currency exchange operations while maintaining reliability through multiple fallback mechanisms.
