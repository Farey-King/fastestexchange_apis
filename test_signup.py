#!/usr/bin/env python3
"""
Test script to verify the signup functionality
"""
import os
import sys
import requests
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fastestexchange_apis.settings')

import django
django.setup()

from fastest_exchange.models import User, Signup, VerificationCode

def test_signup_endpoint():
    """Test the signup endpoint"""
    
    # Test data
    test_email = f"testuser_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    
    print(f"🧪 Testing signup with email: {test_email}")
    
    # Make request to signup endpoint
    url = "http://localhost:8000/api/auth/signup"
    data = {
        "email": test_email
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"📡 Response Status: {response.status_code}")
        print(f"📄 Response Data: {response.json()}")
        
        if response.status_code == 201:
            print("✅ Signup API call successful!")
            
            # Check database records
            check_database_records(test_email)
            
        else:
            print("❌ Signup API call failed!")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Django development server is running on port 8000")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_database_records(email):
    """Check if records were created in database"""
    
    print("\n🔍 Checking database records...")
    
    try:
        # Check User model
        user = User.objects.filter(email=email).first()
        if user:
            print(f"✅ User record found: ID {user.id}, Email: {user.email}, Active: {user.is_active}")
        else:
            print("❌ No User record found")
            
        # Check Signup model
        signup = Signup.objects.filter(email=email).first()
        if signup:
            print(f"✅ Signup record found: Email: {signup.email}, Created: {signup.created_at}")
        else:
            print("❌ No Signup record found")
            
        # Check VerificationCode model
        verification_code = VerificationCode.objects.filter(user__email=email).first()
        if verification_code:
            print(f"✅ Verification code found: Code: {verification_code.code}, Type: {verification_code.code_type}, Expires: {verification_code.expires_at}")
        else:
            print("❌ No VerificationCode record found")
            
    except Exception as e:
        print(f"❌ Database check error: {e}")

def cleanup_test_users():
    """Clean up test users from previous runs"""
    
    print("\n🧹 Cleaning up test users...")
    
    try:
        # Delete test users (emails containing 'testuser_')
        test_users = User.objects.filter(email__contains='testuser_')
        count = test_users.count()
        test_users.delete()
        
        # Delete test signup records
        test_signups = Signup.objects.filter(email__contains='testuser_')
        test_signups.delete()
        
        print(f"✅ Cleaned up {count} test user records")
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Signup Functionality Test\n")
    
    # Cleanup previous test data
    cleanup_test_users()
    
    # Test signup endpoint
    test_signup_endpoint()
    
    print("\n🏁 Test completed!")
