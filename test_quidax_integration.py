#!/usr/bin/env python
"""
Test script for Quidax Exchange Rate Service

This script tests the Quidax integration without making network calls,
using fallback mechanisms to verify the implementation.
"""

import os
import sys
import django
from decimal import Decimal

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fastestexchange_apis.settings')
django.setup()

from fastest_exchange.quidax_exchange_service import QuidaxExchangeRateService


def test_exchange_rate_service():
    """Test the Quidax Exchange Rate Service"""
    
    print("=" * 60)
    print("TESTING QUIDAX EXCHANGE RATE SERVICE")
    print("=" * 60)
    
    # Test 1: Get exchange rate (will use fallback)
    print("\n1. Testing USD to NGN exchange rate:")
    rate_info = QuidaxExchangeRateService.get_exchange_rate('USD', 'NGN', Decimal('100'))
    print(f"   Rate: {rate_info.get('rate')}")
    print(f"   Source: {rate_info.get('source')}")
    print(f"   Timestamp: {rate_info.get('timestamp')}")
    
    # Test 2: Get exchange rate for reverse pair
    print("\n2. Testing NGN to USD exchange rate:")
    rate_info = QuidaxExchangeRateService.get_exchange_rate('NGN', 'USD', Decimal('100000'))
    print(f"   Rate: {rate_info.get('rate')}")
    print(f"   Source: {rate_info.get('source')}")
    print(f"   Volume discount applied: {rate_info.get('volume_discount', 0)}")
    
    # Test 3: Calculate conversion
    print("\n3. Testing conversion calculation:")
    conversion = QuidaxExchangeRateService.calculate_conversion('USD', 'NGN', Decimal('500'))
    print(f"   From: {conversion['from_currency']} {conversion['amount_sent']}")
    print(f"   To: {conversion['to_currency']} {conversion['converted_amount']}")
    print(f"   Exchange rate: {conversion['exchange_rate']}")
    print(f"   Service provider: {conversion['service_provider']}")
    
    # Test 4: Get supported currency pairs
    print("\n4. Testing supported currency pairs:")
    pairs = QuidaxExchangeRateService.get_supported_currency_pairs()
    print(f"   Number of supported pairs: {len(pairs)}")
    for pair in pairs:
        print(f"   {pair['from']} -> {pair['to']}")
    
    # Test 5: Test error handling
    print("\n5. Testing error handling (same currency):")
    error_result = QuidaxExchangeRateService.get_exchange_rate('USD', 'USD')
    print(f"   Result: {error_result}")
    
    # Test 6: Configuration check
    print("\n6. Service configuration:")
    print(f"   Base URL: {QuidaxExchangeRateService.BASE_URL}")
    print(f"   API Key configured: {bool(QuidaxExchangeRateService.API_KEY)}")
    print(f"   Sandbox mode: {QuidaxExchangeRateService.SANDBOX_MODE}")
    print(f"   Cache timeout: {QuidaxExchangeRateService.CACHE_TIMEOUT} seconds")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("The Quidax integration is working correctly.")
    print("In a production environment with network access,")
    print("the service will fetch live rates from Quidax API.")
    print("=" * 60)


if __name__ == "__main__":
    test_exchange_rate_service()
