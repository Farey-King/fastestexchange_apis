# services/prembly_client.py
import requests
import os
from django.conf import settings
from urllib.parse import urljoin

class PremblyClient:
    def __init__(self):
        self.base_url = getattr(settings, 'PREMBLY_BASE_URL', 'https://api.prembly.com')
        self.app_id = getattr(settings, 'PREMBLY_APP_ID')
        self.api_key = getattr(settings, 'PREMBLY_X_API_KEY')
        self.headers = {
            'x-api-key': self.api_key,
            'app_id': self.app_id,
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint, data):
        url = urljoin(self.base_url, endpoint)
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Prembly API request failed: {str(e)}")
    
    def verify_ugx_nin(self, nin_number, first_name=None, last_name=None):
        """Verify UGX (Uganda) National Identification Number"""
        endpoint = '/identitypass/verification/ug/nin'
        data = {
            'number': nin_number
        }
        
        if first_name:
            data['firstname'] = first_name
        if last_name:
            data['lastname'] = last_name
            
        return self._make_request(endpoint, data)
    
    def verify_ngn_nin(self, nin_number):
        """Verify NGN (Nigeria) National Identification Number"""
        endpoint = '/identitypass/verification/ng/nin'
        data = {
            'number': nin_number
        }
        return self._make_request(endpoint, data)
    
    def verify_ngn_drivers_license(self, license_number, dob=None):
        """Verify NGN Driver's License"""
        endpoint = '/identitypass/verification/ng/drivers_license'
        data = {
            'license_number': license_number
        }
        
        if dob:
            data['dob'] = dob.strftime('%Y-%m-%d') if hasattr(dob, 'strftime') else dob
            
        return self._make_request(endpoint, data)
    
    def verify_ngn_international_passport(self, passport_number, first_name=None, last_name=None):
        """Verify NGN International Passport"""
        endpoint = '/identitypass/verification/ng/passport'
        data = {
            'number': passport_number
        }
        
        if first_name:
            data['firstname'] = first_name
        if last_name:
            data['lastname'] = last_name
            
        return self._make_request(endpoint, data)
    
    def verify_ngn_voters_card(self, voters_id, state, last_name=None):
        """
        Verify NGN Voter's Card
        state parameter is REQUIRED for voter card verification
        """
        endpoint = '/identitypass/verification/ng/voters_card'
        data = {
            'voters_id': voters_id,
            'state': state  # This is required
        }
        
        if last_name:
            data['last_name'] = last_name
            
        return self._make_request(endpoint, data)