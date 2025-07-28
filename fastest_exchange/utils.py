# utils.py
import random
import requests
import os


TERMII_API_KEY = os.getenv('TL1pMOaRvnnSXEkTCcmd508MTg2GCVFoTR2NooVMtUqKl9qWnFl9duMHUgsF3i')  # or hardcode for testing (not recommended)
TERMII_SENDER_ID = 'N-Alert'  # e.g. 'N-Alert' (must be approved by Termii)
TERMII_BASE_URL = 'https://v3.api.termii.com'

def format_phone_number(phone_number: str) -> str:
    """Format phone number to international format
    
    Args:
        phone_number: The phone number to format
        
    Returns:
        Formatted phone number in international format
    """
    # Remove any spaces, hyphens, or other characters
    phone = phone_number.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # If it starts with 0 (Nigerian local format), replace with +234
    if phone.startswith('0'):
        phone = '+234' + phone[1:]
    # If it starts with 234 but no +, add +
    elif phone.startswith('234'):
        phone = '+' + phone
    # If it doesn't start with + and doesn't start with 0, assume it needs +234
    elif not phone.startswith('+'):
        # For Nigerian numbers that might be missing the leading 0
        if len(phone) == 10:
            phone = '+234' + phone
        else:
            phone = '+234' + phone
    
    return phone

def send_otp_to_phone(phone_number: str, otp_code: str):
    """Send OTP to phone number using Termii SMS API
    
    Args:
        phone_number: The phone number to send OTP to
        otp_code: The OTP code to send
    """
    
    # Format phone number to international format
    formatted_phone = format_phone_number(phone_number)
    print(f"[DEBUG] Original phone: {phone_number}, Formatted: {formatted_phone}")
    
    # Use Termii SMS API to send the custom OTP
    url = f"{TERMII_BASE_URL}/api/sms/send"
    
    message = f"Your Fastest Exchange verification code is {otp_code}. This code expires in 5 minutes. Do not share this code with anyone."
    
    payload = {
        "api_key": "TL1pMOaRvnnSXEkTCcmd508MTg2GCVFoTR2NooVMtUqKl9qWnFl9duMHUgsF3i",
        "to": formatted_phone,
        "from": "N-Alert",
        "sms": message,
        "type": "plain",
        "channel": "generic",
    }

    try:
        print(f"[DEBUG] Sending SMS to {formatted_phone} with OTP: {otp_code}")
        response = requests.post(url, json=payload, timeout=30)
        print(f"[DEBUG] Termii API Response Status: {response.status_code}")
        print(f"[DEBUG] Termii API Response: {response.text}")
        
        if response.status_code == 200:
            return {
                "status": "success", 
                "message": "OTP sent successfully",
                "termii_response": response.json()
            }
        else:
            return {
                "status": "error", 
                "message": f"Failed to send SMS. Status: {response.status_code}",
                "termii_response": response.text
            }
            
    except requests.RequestException as e:
        print(f"[DEBUG] SMS sending failed: {e}")
        return {
            "status": "error", 
            "message": "Failed to send SMS due to network error",
            "error": str(e)
        }



def generate_otp():
    return str(random.randint(100000, 999999))
