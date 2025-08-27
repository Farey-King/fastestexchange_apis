from django.test import TestCase
# test_prembly.py
import os
import django
import requests
from pathlib import Path
import dotenv #type: ignore 

# Load environment variables
env_path = Path(__file__).resolve().parent / '.env'
dotenv.load_dotenv(env_path)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fastest_exchange.settings')
try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")

def test_prembly_credentials():
    """Test if Prembly credentials are working"""
    print("Testing Prembly credentials...")
    
    # Get credentials from environment
    app_id = os.getenv('PREMBLY_APP_ID')
    api_key = os.getenv('PREMBLY_API_KEY')
    
    print(f"App ID: {app_id}")
    print(f"API Key: {api_key}")
    
    if not app_id or not api_key:
        print("❌ Prembly credentials not found in environment variables")
        print("Please check your .env file")
        return

    url = " https://api.prembly.com/identitypass/verification/vnin"

    headers = {
        'x-api-key': api_key,
        'app_id': app_id,
        'Content-Type': 'application/json'
    }
    
    # Test data - use a valid test NIN
    data = {
        "number": "40270119123"
    }


    try:
        print("Sending request to Prembly...")
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 401:
            print("❌ Authentication failed - check your API keys")
        elif response.status_code == 403:
            print("❌ Forbidden - check your subscription/plan")
        elif response.status_code == 200:
            print("✅ Credentials are working!")
            result = response.json()
            print(f"Verification status: {result.get('status')}")
            print(f"Message: {result.get('message')}")
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - check your internet connection")
    except requests.exceptions.Timeout:
        print("❌ Request timeout - Prembly API is not responding")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_prembly_credentials()
# Create your tests here.
