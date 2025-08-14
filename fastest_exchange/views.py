from django.shortcuts import render

# Create your views here.
import os
from datetime import datetime, timedelta
from typing import Dict, List, Type

from django.contrib.auth import update_session_auth_hash, get_user_model, authenticate
from django.db import IntegrityError 
# from django.db import models 
from django.db.models import ProtectedError 
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse 


# To bypass having a CSRF token
# from django_renderpdf.views import PDFView  # Removed due to unresolved import
import requests
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token 
from rest_framework.authtoken.views import ObtainAuthToken 
from rest_framework.decorators import action, api_view, permission_classes 
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request 
from rest_framework.response import Response 
from rest_framework.views import APIView 
from rest_framework_simplejwt.views import InvalidToken, TokenError, TokenObtainPairView 
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password, check_password 
from django.utils import timezone 
from datetime import timedelta
from django.core.mail import send_mail,EmailMessage 
from django.views.decorators.csrf import csrf_exempt 
from django.utils.decorators import method_decorator 
from django.conf import settings 
from django.urls import reverse 
from .utils import send_otp_to_phone, get_live_rates

from drf_spectacular.utils import extend_schema

import random,uuid
import string
from io import StringIO
import csv
from fastest_exchange import models

# from fastest_exchange.messaging.email import send_password_reset_email
# from fastest_exchange.messaging.exchange_rate import ExchangeRateNotification

# from .filters import DefaultFilter, OrderingFilter, SearchFilter, TransactionFilter
from .models import (
    User,
    VerificationCode,  # Added import for VerificationCode
    Signup,  # Added import for Signup
    CompleteSignup,  # Added import for CompleteSignup
    CreatePassword,  # Added import for CreatePassword
    CreatePin,  # Added import for CreatePin
    Login,  # Added import for Login
    PhoneNumber,  # Added import for PhoneNumber
    SwapEngine,
    SavedBeneficiary,  # Added import for SavedBeneficiary
    KYC,
)

from .serializers import (
   
    MyTokenObtainPairSerializer,
   
     # Added import for UserLoginSerializer
    PINSerializer,
    # SavedBeneficiarySerializer,  # Added import for PINSerializer
    VerificationCodeSerializer,  # Added import for VerificationCodeSerializer
    SignupSerializer,  # Added import for SignupSerializer
    
    CreatePasswordSerializer,  # Added import for CreatePasswordSerializer
    CompleteSignupSerializer,  # Added import for CompleteProfileSerializer
    CreatePinSerializer,  # Added import for CreatePinSerializer
    LoginSerializer,  # Added import for LoginSerializer
    SignupSerializer,  # Added import for SignupSerializer
    SendOTPSerializer,  # Added import for SendOTPSerializer
    VerifyOTPSerializer,  # Added import for VerifyOTPSerializer
    SwapSerializer,  # Added import for SwapSerializer
    SavedBeneficiarySerializer,  # Added import for SavedBeneficiarySerializer
    KYCSerializer,  # Added import for KYCSerializer
    
    # Transaction Engine serializers
    TransactionSerializer,
    TransactionCreateSerializer,
    TransactionUpdateStatusSerializer,
    TransactionListSerializer,
    TransactionStatusHistorySerializer,
)


@method_decorator(csrf_exempt, name='dispatch')
class SignupView(APIView):
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']

        print(f"Received email: {email}")

        # Check if user already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "A user with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Create inactive user - ensure proper save
            user = User.objects.create_user(
                email=email,
                is_active=False,  # User is inactive until they verify email
                password=None  # No password yet
            )
            user.save()  # Explicitly save to ensure database persistence
            
            print(f"User created with ID: {user.id}")

            # Also create a Signup record for tracking
            signup_record, created = Signup.objects.get_or_create(
                email=email,
                defaults={}
            )
            print(f"Signup record created: {created}")

            # Generate verification token
            token = str(uuid.uuid4())
            expires_at = timezone.now() + timezone.timedelta(minutes=30)

            VerificationCode.objects.create(
                user=user,
                code=token,
                code_type='email',
                expires_at=expires_at
            )
            print(f"Verification code created: {token}")

            # Build verification link
            verification_url = (
                f"{settings.FRONTEND_URL}/create-password"
                f"?token={token}&email={email}"
            )

            print(f"Verification URL: {verification_url}")

            # Send email
            try:
                email_message = EmailMessage(
                    subject="Verify Your Email - Fastest Exchange",
                    body=f"""
Hello!

Welcome to Fastest Exchange! Thanks for signing up.

To complete your registration, please verify your email address and set your password by clicking the link below:

{verification_url}

This verification link will expire in 30 minutes.

If you didn't create an account with us, you can safely ignore this email.

Best regards,
The Fastest Exchange Team
""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                
                # In development with DEBUG=True, this will print to console
                # In production, it will actually send the email
                email_message.send(fail_silently=False)
                
                print(f"Verification email sent to: {email}")
                
                return Response(
                    {
                        "message": "Account created successfully! Please check your email to verify your account and set your password.",
                        "email": email,
                        "user_id": user.id
                    },
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                print(f"Email sending failed: {e}")
                # Even if email fails, user is created, so inform the user
                return Response(
                    {
                        "message": "Account created but email sending failed. Please contact support.",
                        "email": email,
                        "user_id": user.id,
                        "error": str(e)
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            print(f"User creation failed: {e}")
            return Response(
                {"error": f"Failed to create user: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema(
    request=SendOTPSerializer,
    responses={200: None},
    description="Send OTP to a phone number"
)
@method_decorator(csrf_exempt, name='dispatch')
class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        print(f"[DEBUG] Request data: {request.data}")
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone_number']
            generated_otp = serializer.validated_data['generated_otp']
            print(f"[DEBUG] Phone number: {phone}")
            print(f"[DEBUG] Generated OTP: {generated_otp}")
            
            # Send OTP via SMS using Termii API
            result = send_otp_to_phone(phone, generated_otp)
            
            return Response(
                {
                    "message": "OTP sent successfully.",
                    "phone_number": phone,
                    "otp_generated": True
                },
                status=status.HTTP_200_OK
            )
        print(f"[DEBUG] Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@extend_schema(
    request=VerifyOTPSerializer,
    responses={200: None},
    description="Verify OTP for a phone number"
)
@method_decorator(csrf_exempt, name='dispatch')
class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        print(f"[DEBUG] OTP Verification Request data: {request.data}")
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            # The validation in the serializer handles the OTP verification
            # If we reach this point, the OTP was valid
            phone = serializer.validated_data['phone_number']
            otp = serializer.validated_data['otp']
            print(f"[DEBUG] OTP verified successfully for {phone}")
            
            return Response(
                {
                    "message": "Phone number verified successfully.",
                    "phone_number": phone,
                    "verified": True
                },
                status=status.HTTP_200_OK
            )
        print(f"[DEBUG] OTP Verification errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# views.py
@method_decorator(csrf_exempt, name='dispatch')
class CreatePasswordView(APIView):
    serializer_class = CreatePasswordSerializer
    permission_classes = []
    @method_decorator(csrf_exempt)
    def post(self, request):
        serializer = CreatePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Set password for user with given email
    
        # email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        token = serializer.validated_data['token']

        
        try:
            # Find the verification code
            code = VerificationCode.objects.get(code=token, code_type='email')
        except VerificationCode.DoesNotExist:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        if code.expires_at < timezone.now():
            return Response({"error": "Token has expired."}, status=status.HTTP_400_BAD_REQUEST)

        user = code.user
        user.set_password(password)
        user.is_active = True  # Activate user after setting password
        user.save()

        # Mark the verification code as used
        code.is_used = True
        code.save()

        return Response(
            {"message": "Password set. Please complete your profile."},
            status=status.HTTP_200_OK
        )

# views.py
@method_decorator(csrf_exempt, name='dispatch')
class CompleteSignupView(APIView):
    serializer_class = CompleteSignupSerializer
    permission_classes = [permissions.AllowAny]
    @method_decorator(csrf_exempt)
    def post(self, request):
        serializer = CompleteSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Update user profile logic here
        email = serializer.validated_data['email']
        first_name = serializer.validated_data['first_name']
        last_name = serializer.validated_data['last_name']
        phone_number = serializer.validated_data['phone_number']
        country = serializer.validated_data['country']

        user, created = User.objects.get_or_create(email=email)

        user.first_name = first_name
        user.last_name = last_name
        user.phone_number = phone_number  # If you have this field on your user model
        user.country = country  # Same, make sure your User model has this field if needed
        user.save()

        # Save extended profile in CompleteSignup
        CompleteSignup.objects.update_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
                'country': country,
                'date_of_birth': serializer.validated_data['date_of_birth'],
                'residential_area_1': serializer.validated_data['residential_area_1'],
                'residential_area_2': serializer.validated_data['residential_area_2'],
                'area': serializer.validated_data['area'],
                'town_city': serializer.validated_data['town_city'],
                'occupation': serializer.validated_data['occupation'],
                'postal_code': serializer.validated_data['postal_code'],
            }
        )
        # ...
        return Response(
            {"message": "Profile completed. Please set your PIN."},
            status=status.HTTP_200_OK
        )


# views.py
@method_decorator(csrf_exempt, name='dispatch')
class CreatePinView(APIView):
    serializer_class = CreatePinSerializer
    permission_classes = [permissions.AllowAny]
    @method_decorator(csrf_exempt)
    def post(self, request):
        serializer = CreatePinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Set PIN for user logic here (hash and save)
        # pin = serializer.validated_data['pin']
        

        # ...
        return Response(
            {"message": "PIN set. Signup complete!"},
            status=status.HTTP_200_OK
        )
User = get_user_model()


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        # ✅ 1) Check if the user exists and the password is correct
        user = authenticate(request, email=email, password=password)

        if not user:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # ✅ 2) Check if the user is active
        if not user.is_active:
            return Response(
                {"detail": "Account not active. Please verify your email."},
                status=status.HTTP_403_FORBIDDEN
            )

        # ✅ 3) Issue JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "message": "Login successful."
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class SwapView(APIView):
    serializer_class = SwapSerializer
    permission_classes = [IsAuthenticated] 

    def post(self, request):
        serializer = SwapSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        data = serializer.validated_data
        
        from_currency = data["currency_from"].upper()
        to_currency = data["currency_to"].upper()
        amount_sent = float(data["amount_sent"])
        payment_method = data["payment_method"]

        # Validate currency pair
        if from_currency == to_currency:
            return Response({"error": "Cannot exchange the same currency."}, status=400)
        
        # Calculate conversion using swap engine logic
        swap_result = self.calculate_swap(
            from_currency=from_currency,
            to_currency=to_currency,
            amount_sent=amount_sent
        )
        
        if "error" in swap_result:
            return Response({"error": swap_result["error"]}, status=400)
        
        # Create swap transaction record
        transaction = SwapEngine.objects.create(
            currency_from=from_currency,
            currency_to=to_currency,
            amount_sent=amount_sent,
            converted_amount=round(swap_result["converted_amount"], 2),
            exchange_rate=round(swap_result["exchange_rate"], 6),
            receiver_account_name=data["receiver_account_name"],
            receiver_account_number=data["receiver_account_number"],
            receiver_bank=data["receiver_bank"],
            payment_method=payment_method,
            verification_mode=data.get("verification_mode", "manual"),
            proof_of_payment=data.get("proof_of_payment"),
            status=data.get("status", "pending"),
        )
        
        # Create corresponding Transaction Engine record for tracking
        try:
            from .models import Transaction, TransactionType, TransactionStatusHistory
            with db_transaction.atomic():
                main_transaction = Transaction.objects.create(
                    user=request.user,
                    transaction_type=TransactionType.SWAP,
                    amount_sent=amount_sent,
                    currency_from=from_currency,
                    amount_received=swap_result["converted_amount"],
                    currency_to=to_currency,
                    exchange_rate=swap_result["exchange_rate"],
                    swap_reference=transaction,
                    metadata={
                        'payment_method': payment_method,
                        'receiver_details': {
                            'account_name': data["receiver_account_name"],
                            'account_number': data["receiver_account_number"],
                            'bank': data["receiver_bank"]
                        }
                    },
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Create status history
                TransactionStatusHistory.objects.create(
                    transaction=main_transaction,
                    old_status=None,
                    new_status='INITIATED',
                    changed_by=request.user,
                    reason='Swap transaction created'
                )
        except Exception as e:
            print(f"Warning: Failed to create Transaction Engine record: {e}")
        
        return Response({
            "message": "Swap created successfully. Awaiting payment.",
            "transaction_id": transaction.id,
            "swap_details": {
                "from_currency": from_currency,
                "to_currency": to_currency,
                "amount_sent": amount_sent,
                "amount_to_receive": round(swap_result["converted_amount"], 2),
                "exchange_rate": round(swap_result["exchange_rate"], 6),
                "rate_type": swap_result["rate_type"]
            },
            "status": transaction.status,
            "receiver_details": {
                "account_name": data["receiver_account_name"],
                "account_number": data["receiver_account_number"],
                "bank": data["receiver_bank"]
            },
            "payment_method": payment_method
        }, status=201)
    
    def calculate_swap(self, from_currency: str, to_currency: str, amount_sent: float) -> dict:
        """
        Dynamic Swap Engine Logic Implementation
        
        Uses ExchangeRateService for dynamic rate calculation with:
        - Database rates (most recent)
        - Third-party API rates (live market rates) 
        - Fallback static rates
        - Amount-based pricing
        - Margin and volume discounts
        """
        from .exchange_rate_service import ExchangeRateService
        from decimal import Decimal
        
        try:
            # Convert amount to Decimal for precise calculations
            amount_decimal = Decimal(str(amount_sent))
            
            # Get dynamic exchange rate
            conversion_result = ExchangeRateService.calculate_conversion(
                from_currency=from_currency,
                to_currency=to_currency, 
                amount=amount_decimal
            )
            
            if 'error' in conversion_result:
                return conversion_result
            
            # Extract rate info for response
            rate_info = conversion_result.get('rate_info', {})
            rate_source = rate_info.get('source', 'unknown')
            
            # Build rate type description
            rate_descriptions = {
                'database': 'Live Database Rate',
                'fixer': 'Live Market Rate (Fixer.io)',
                'exchangerate_api': 'Live Market Rate (ExchangeRate-API)', 
                'currencyapi': 'Live Market Rate (CurrencyAPI)',
                'fallback_static': 'Static Fallback Rate'
            }
            
            rate_type = f"{from_currency} to {to_currency} - {rate_descriptions.get(rate_source, 'Unknown Source')}"
            
            # Add margin and volume discount info if available
            if 'margin_applied' in rate_info:
                margin_pct = rate_info['margin_applied'] * 100
                rate_type += f" (Margin: {margin_pct:.1f}%)"
            
            if 'volume_discount' in rate_info and rate_info['volume_discount'] > 0:
                discount_pct = rate_info['volume_discount'] * 100
                rate_type += f" (Volume Discount: {discount_pct:.1f}%)"
            
            return {
                "converted_amount": conversion_result['converted_amount'],
                "exchange_rate": conversion_result['exchange_rate'],
                "rate_type": rate_type,
                "rate_source": rate_source,
                "rate_info": rate_info,
                "calculation_timestamp": conversion_result.get('calculation_time')
            }
            
        except Exception as e:
            # Log the error and return fallback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in dynamic rate calculation: {e}")
            
            # Fallback to static calculation for reliability
            return self._calculate_swap_fallback(from_currency, to_currency, amount_sent)
    
    def _calculate_swap_fallback(self, from_currency: str, to_currency: str, amount_sent: float) -> dict:
        """
        Fallback to original static rate calculation if dynamic rates fail
        """
        # Define exchange rates
        EXCHANGE_RATES = {
            'NGN_TO_USD': 1610,  # Divide NGN by 1610 to get USD
            'USD_TO_NGN': 1550,  # Multiply USD by 1550 to get NGN
            'UGX_TO_NGN': 2.35,    # Example rate, adjust as needed
            'NGN_TO_UGX': 2.27,  # Example rate, adjust as needed
        }
        
        # Supported currency pairs
        SUPPORTED_PAIRS = [
            ('NGN', 'USD'),
            ('USD', 'NGN'),
            ('NGN', 'UGX'),
            ('UGX', 'NGN'),
        ]
        
        # Check if currency pair is supported
        if (from_currency, to_currency) not in SUPPORTED_PAIRS:
            return {
                "error": f"Currency pair {from_currency} to {to_currency} is not supported. "
                        "Supported pairs: NGN↔USD, NGN↔UGX"
            }
        
        # Calculate conversion based on direction
        if from_currency == 'NGN' and to_currency == 'USD':
            # NGN to USD: NGN / 1610 = USD
            rate = EXCHANGE_RATES['NGN_TO_USD']
            converted_amount = amount_sent / rate
            exchange_rate = 1 / rate  # Rate per 1 NGN
            rate_type = "NGN to USD (Static Fallback)"

        elif from_currency == 'UGX' and to_currency == 'NGN':
            # UGX to NGN: UGX * 2.35 = NGN
            rate = EXCHANGE_RATES['UGX_TO_NGN']
            converted_amount = amount_sent * rate
            exchange_rate = rate  # Rate per 1 UGX
            rate_type = "UGX to NGN (Static Fallback)"
            
        elif from_currency == 'NGN' and to_currency == 'UGX':
            # NGN to UGX: NGN * 2.27 = UGX
            rate = EXCHANGE_RATES['NGN_TO_UGX']
            converted_amount = amount_sent * rate
            exchange_rate = rate  # Rate per 1 NGN
            rate_type = "NGN to UGX (Static Fallback)"

        elif from_currency == 'USD' and to_currency == 'NGN':
            # USD to NGN: USD * 1550 = NGN
            rate = EXCHANGE_RATES['USD_TO_NGN']
            converted_amount = amount_sent * rate
            exchange_rate = rate  # Rate per 1 USD
            rate_type = "USD to NGN (Static Fallback)"
            
        else:
            return {"error": "Unsupported currency conversion"}
        
        return {
            "converted_amount": converted_amount,
            "exchange_rate": exchange_rate,
            "rate_type": rate_type,
            "rate_source": "static_fallback"
        }
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
class ManualVerifyView(APIView):

    """
    Manually verify a swap transaction.
    Only accessible by admin users.
    """
    queryset = SwapEngine.objects.all()
    serializer_class = SwapSerializer
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, transaction_id):
        swap = get_object_or_404(SwapEngine, id=transaction_id)
        if swap.transaction_status != "pending_verification":
            return Response({"error": "Transaction not in verification stage"}, status=400)

        swap.transaction_status = "verified"
        swap.save()
        return Response({"message": "Transaction manually verified"})
    
class SavedBeneficiaryView(generics.ListCreateAPIView):
    serializer_class = SavedBeneficiarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedBeneficiary.objects.filter(user=self.request.user)
    
class SavedBeneficiaryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SavedBeneficiarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedBeneficiary.objects.filter(user=self.request.user)
    
# --- USER SUBMITS KYC ---
class KYCSubmissionView(generics.CreateAPIView):
    serializer_class = KYCSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


    def perform_update(self, serializer):
        serializer.save(
            reviewed_by=self.request.user,
            reviewed_at=timezone.now()
        )

@csrf_exempt
def send_verification_code(user, code_type):
    code = ''.join(random.choices(string.digits, k=6))
    expires_at = timezone.now() + timedelta(minutes=10)
    
    VerificationCode.objects.create(
        user=user,
        code=code,
        code_type=code_type,
        expires_at=expires_at
    )
    
    if code_type == 'email':
        send_mail(
            'Verify Your Email',
            f'Your verification code is: {code}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def create_pin(request):
    serializer = PINSerializer(data=request.data)
    if serializer.is_valid():
        pin = serializer.validated_data['pin']
        request.user.pin = make_password(pin)
        request.user.save()
        
        return Response({
            'message': 'PIN created successfully'
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def verify_pin(request):
    serializer = PINSerializer(data=request.data)
    if serializer.is_valid():
        pin = serializer.validated_data['pin']
        user = request.user
        
        # Check if PIN is locked
        if user.pin_locked_until and user.pin_locked_until > timezone.now():
            return Response({
                'error': 'PIN is temporarily locked. Try again later.'
            }, status=status.HTTP_423_LOCKED)
        
        if user.pin and check_password(pin, user.pin):
            user.pin_attempts = 0
            user.pin_locked_until = None
            user.save()
            return Response({
                'message': 'PIN verified successfully'
            }, status=status.HTTP_200_OK)
        else:
            user.pin_attempts += 1
            if user.pin_attempts >= 3:
                user.pin_locked_until = timezone.now() + timedelta(minutes=15)
            user.save()
            
            return Response({
                'error': f'Invalid PIN. Attempts: {user.pin_attempts}/3'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def verify_email(request):
    serializer = VerificationCodeSerializer(data=request.data)
    if serializer.is_valid():
        code = serializer.validated_data['code']
        
        verification = VerificationCode.objects.filter(
            code=code,
            verify_email='email',
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()
        
        if verification:
            user = verification.user
            user.is_email_verified = True
            user.save()
            
            verification.is_used = True
            verification.save()
            
            return Response({
                'message': 'Email verified successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Invalid or expired verification code'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def resend_verification_code(request):
    email = request.data.get('email')
    code_type = request.data.get('code_type', 'email')
    
    try:
        user = User.objects.get(email=email)
        
        # Invalidate existing codes
        VerificationCode.objects.filter(
            user=user,
            code_type=code_type,
            is_used=False
        ).update(is_used=True)
        
        # Generate new code
        code = ''.join(random.choices(string.digits, k=6))
        expires_at = timezone.now() + timedelta(minutes=10)
        
        VerificationCode.objects.create(
            user=user,
            code=code,
            code_type=code_type,
            expires_at=expires_at
        )
        
        if code_type == 'email':
            send_mail(
                'Verify Your Email',
                f'Your verification code is: {code}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        
        return Response({
            'message': f'Verification code sent to {code_type}'
        }, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@csrf_exempt
def logout(request):
    try:
        token = Token.objects.get(user=request.user)
        token.delete()
        return Response({
            'message': 'Logged out successfully'
        }, status=status.HTTP_200_OK)
    except Token.DoesNotExist:
        return Response({
            'error': 'Token not found'
        }, status=status.HTTP_400_BAD_REQUEST)


class AuthTokenView(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        """Override default auth method to to include user object"""

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": user})










class MyTokenObtainPairView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


#




def index(request):
    """
    render index page
    :param request: request object
    :return: page
    """

    return render(request, "index.html")


# ==================================================
# TRANSACTION ENGINE VIEWS
# ==================================================

from .models import (
    Transaction, 
    TransactionStatusHistory, 
    TransactionType, 
    TransactionStatus,
    SwapEngine,
    BankTransfer,
    MobileMoney,
    ReceiveCash,
    KYC,
    SavedBeneficiary
)
from django.db import transaction as db_transaction
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

class TransactionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

@extend_schema(
    tags=['Transaction Engine'],
    summary='Create a new transaction',
    description='''
    Create a new transaction of any type (SWAP, BANK_TRANSFER, MOBILE_MONEY, etc.).
    This endpoint provides unified transaction creation with automatic ID assignment 
    and comprehensive tracking capabilities.
    '''
)
class TransactionCreateView(APIView):
    """Create transactions with automatic ID assignment and tracking"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionCreateSerializer
    
    def post(self, request):
        serializer = TransactionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        transaction_type = data['transaction_type']
        
        try:
            with db_transaction.atomic():
                # Create the main transaction record
                transaction_obj = Transaction.objects.create(
                    user=request.user,
                    transaction_type=transaction_type,
                    amount_sent=data.get('amount_sent'),
                    currency_from=data.get('currency_from'),
                    amount_received=data.get('amount_received'),
                    currency_to=data.get('currency_to'),
                    exchange_rate=data.get('exchange_rate'),
                    metadata=data.get('metadata', {}),
                    notes=data.get('notes', ''),
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
                
                # Create transaction-specific record based on type
                specific_transaction = self.create_specific_transaction(
                    transaction_type, 
                    data.get('transaction_data', {}), 
                    transaction_obj,
                    request.user
                )
                
                # Link the specific transaction to the main transaction
                self.link_specific_transaction(transaction_obj, specific_transaction, transaction_type)
                
                # Create initial status history
                TransactionStatusHistory.objects.create(
                    transaction=transaction_obj,
                    old_status=None,
                    new_status=TransactionStatus.INITIATED,
                    changed_by=request.user,
                    reason='Transaction created'
                )
                
                response_data = {
                    'transaction_id': transaction_obj.transaction_id,
                    'id': transaction_obj.id,
                    'transaction_type': transaction_obj.transaction_type,
                    'status': transaction_obj.status,
                    'created_at': transaction_obj.created_at,
                    'message': f'{transaction_type} transaction created successfully'
                }
                
                if specific_transaction and hasattr(specific_transaction, 'id'):
                    response_data['specific_transaction_id'] = specific_transaction.id
                
                return Response(response_data, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response(
                {'error': f'Failed to create transaction: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create_specific_transaction(self, transaction_type, transaction_data, main_transaction, user):
        """Create transaction-specific records"""
        
        if transaction_type == TransactionType.SWAP:
            # For swap transactions, we might create a SwapEngine record
            return SwapEngine.objects.create(
                currency_from=main_transaction.currency_from or 'USD',
                currency_to=main_transaction.currency_to or 'UGX',
                amount_sent=main_transaction.amount_sent or 0,
                converted_amount=main_transaction.amount_received or 0,
                exchange_rate=float(main_transaction.exchange_rate or 1),
                receiver_account_name=transaction_data.get('receiver_account_name', ''),
                receiver_account_number=transaction_data.get('receiver_account_number', ''),
                receiver_bank=transaction_data.get('receiver_bank', ''),
                payment_method=transaction_data.get('payment_method', 'bank_transfer'),
                verification_mode=transaction_data.get('verification_mode', 'manual'),
                status='pending'
            )
        
        elif transaction_type == TransactionType.BANK_TRANSFER:
            return BankTransfer.objects.create(
                user=user,
                amount_sent=main_transaction.amount_sent,
                currency_from=main_transaction.currency_from,
                amount_received=main_transaction.amount_received,
                currency_to=main_transaction.currency_to,
                receiver_account_name=transaction_data.get('receiver_account_name', ''),
                receiver_account_number=transaction_data.get('receiver_account_number', ''),
                receiver_bank=transaction_data.get('receiver_bank', ''),
                bank=transaction_data.get('bank', ''),
                account_number=transaction_data.get('account_number', ''),
                account_name=transaction_data.get('account_name', ''),
                narration=transaction_data.get('narration', ''),
                status='pending'
            )
        
        elif transaction_type == TransactionType.MOBILE_MONEY:
            return MobileMoney.objects.create(
                user=user,
                amount_sent=main_transaction.amount_sent,
                currency_from=main_transaction.currency_from,
                amount_received=main_transaction.amount_received,
                currency_to=main_transaction.currency_to,
                receiver_name=transaction_data.get('receiver_name', ''),
                receiver_number=transaction_data.get('receiver_number', ''),
                narration=transaction_data.get('narration', ''),
                status='pending'
            )
        
        elif transaction_type == TransactionType.CASH_PICKUP:
            return ReceiveCash.objects.create(
                user=user,
                amount_sent=main_transaction.amount_sent,
                currency_from=main_transaction.currency_from,
                amount_received=main_transaction.amount_received,
                currency_to=main_transaction.currency_to,
                receiver_name=transaction_data.get('receiver_name', ''),
                receiver_IDnumber=transaction_data.get('receiver_id_number', ''),
                receiver_phone_number=transaction_data.get('receiver_phone', ''),
                narration=transaction_data.get('narration', ''),
                status='pending'
            )
        
        return None
    
    def link_specific_transaction(self, main_transaction, specific_transaction, transaction_type):
        """Link specific transaction to main transaction"""
        if not specific_transaction:
            return
            
        if transaction_type == TransactionType.SWAP:
            main_transaction.swap_reference = specific_transaction
        elif transaction_type == TransactionType.BANK_TRANSFER:
            main_transaction.bank_transfer_reference = specific_transaction
        elif transaction_type == TransactionType.MOBILE_MONEY:
            main_transaction.mobile_money_reference = specific_transaction
        elif transaction_type == TransactionType.CASH_PICKUP:
            main_transaction.cash_pickup_reference = specific_transaction
        
        main_transaction.save()
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

@extend_schema(
    tags=['Transaction Engine'],
    summary='List all transactions',
    description='''
    Retrieve a paginated list of all transactions for the authenticated user.
    Supports filtering by transaction_type, status, and date ranges.
    '''
)
class TransactionListView(generics.ListAPIView):
    """List transactions with filtering and pagination"""
    
    serializer_class = TransactionListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TransactionPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transaction_type', 'status']
    search_fields = ['transaction_id', 'notes', 'currency_from', 'currency_to']
    ordering_fields = ['created_at', 'updated_at', 'amount_sent']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Transaction.objects.filter(user=self.request.user)
        
        # Date range filtering
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset

@extend_schema(
    tags=['Transaction Engine'],
    summary='Get transaction details',
    description='Retrieve detailed information about a specific transaction including status history.'
)
class TransactionDetailView(generics.RetrieveAPIView):
    """Get detailed transaction information"""
    
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'transaction_id'
    
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

@extend_schema(
    tags=['Transaction Engine'],
    summary='Update transaction status',
    description='''
    Update the status of a transaction. This creates a status history record 
    for audit purposes and can trigger additional business logic.
    '''
)
class TransactionUpdateStatusView(APIView):
    """Update transaction status with history tracking"""
    
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionUpdateStatusSerializer
    
    def patch(self, request, transaction_id):
        try:
            transaction_obj = Transaction.objects.get(
                transaction_id=transaction_id, 
                user=request.user
            )
        except Transaction.DoesNotExist:
            return Response(
                {'error': 'Transaction not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TransactionUpdateStatusSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = transaction_obj.status
        new_status = serializer.validated_data['status']
        reason = serializer.validated_data.get('reason', '')
        notes = serializer.validated_data.get('notes', '')
        
        # Update transaction
        transaction_obj.status = new_status
        if notes:
            transaction_obj.notes = f"{transaction_obj.notes or ''}\n{notes}"
        
        if new_status == TransactionStatus.COMPLETED:
            transaction_obj.completed_at = timezone.now()
        
        transaction_obj.save()
        
        # Create status history
        TransactionStatusHistory.objects.create(
            transaction=transaction_obj,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            reason=reason
        )
        
        # Update linked specific transaction status if needed
        self.update_specific_transaction_status(transaction_obj, new_status)
        
        return Response({
            'transaction_id': transaction_obj.transaction_id,
            'status': transaction_obj.status,
            'message': f'Transaction status updated from {old_status} to {new_status}'
        }, status=status.HTTP_200_OK)
    
    def update_specific_transaction_status(self, transaction_obj, new_status):
        """Update status in linked specific transaction records"""
        status_mapping = {
            TransactionStatus.COMPLETED: 'verified',
            TransactionStatus.FAILED: 'failed',
            TransactionStatus.PENDING: 'pending',
            TransactionStatus.IN_PROGRESS: 'processing'
        }
        
        mapped_status = status_mapping.get(new_status, 'pending')
        
        if transaction_obj.swap_reference:
            transaction_obj.swap_reference.status = mapped_status
            transaction_obj.swap_reference.save()
        
        if transaction_obj.bank_transfer_reference:
            transaction_obj.bank_transfer_reference.status = mapped_status
            transaction_obj.bank_transfer_reference.save()
        
        if transaction_obj.mobile_money_reference:
            transaction_obj.mobile_money_reference.status = mapped_status
            transaction_obj.mobile_money_reference.save()
        
        if transaction_obj.cash_pickup_reference:
            transaction_obj.cash_pickup_reference.status = mapped_status
            transaction_obj.cash_pickup_reference.save()

@extend_schema(
    tags=['Transaction Engine'],
    summary='Get transaction statistics',
    description='Get statistics and analytics for user transactions.'
)
class TransactionStatsView(APIView):
    """Get transaction statistics and analytics"""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        queryset = Transaction.objects.filter(user=user)
        
        # Basic stats
        total_transactions = queryset.count()
        completed_transactions = queryset.filter(status=TransactionStatus.COMPLETED).count()
        pending_transactions = queryset.filter(status=TransactionStatus.PENDING).count()
        failed_transactions = queryset.filter(status=TransactionStatus.FAILED).count()
        
        # Amount stats
        from django.db.models import Sum, Avg
        total_amount_sent = queryset.aggregate(
            total=Sum('amount_sent')
        )['total'] or 0
        
        average_transaction_amount = queryset.aggregate(
            avg=Avg('amount_sent')
        )['avg'] or 0
        
        # Transaction type breakdown
        type_breakdown = {}
        for choice in TransactionType.choices:
            type_code, type_name = choice
            count = queryset.filter(transaction_type=type_code).count()
            type_breakdown[type_code] = {
                'name': type_name,
                'count': count
            }
        
        # Recent activity (last 30 days)
        from datetime import date, timedelta
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_transactions = queryset.filter(created_at__date__gte=thirty_days_ago).count()
        
        return Response({
            'total_transactions': total_transactions,
            'completed_transactions': completed_transactions,
            'pending_transactions': pending_transactions,
            'failed_transactions': failed_transactions,
            'completion_rate': (completed_transactions / total_transactions * 100) if total_transactions > 0 else 0,
            'total_amount_sent': str(total_amount_sent),
            'average_transaction_amount': str(round(average_transaction_amount, 2)),
            'transaction_type_breakdown': type_breakdown,
            'recent_activity_30_days': recent_transactions
        }, status=status.HTTP_200_OK)

@extend_schema(
    tags=['Transaction Engine'],
    summary='Search transactions',
    description='Advanced search functionality for transactions with multiple criteria.'
)
class TransactionSearchView(generics.ListAPIView):
    """Advanced transaction search"""
    
    serializer_class = TransactionListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TransactionPagination
    
    def get_queryset(self):
        user = self.request.user
        queryset = Transaction.objects.filter(user=user)
        
        # Search parameters
        transaction_id = self.request.query_params.get('transaction_id')
        transaction_type = self.request.query_params.get('transaction_type')
        status_param = self.request.query_params.get('status')
        currency_from = self.request.query_params.get('currency_from')
        currency_to = self.request.query_params.get('currency_to')
        amount_min = self.request.query_params.get('amount_min')
        amount_max = self.request.query_params.get('amount_max')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        
        # Apply filters
        if transaction_id:
            queryset = queryset.filter(transaction_id__icontains=transaction_id)
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if currency_from:
            queryset = queryset.filter(currency_from__icontains=currency_from)
        if currency_to:
            queryset = queryset.filter(currency_to__icontains=currency_to)
        if amount_min:
            queryset = queryset.filter(amount_sent__gte=amount_min)
        if amount_max:
            queryset = queryset.filter(amount_sent__lte=amount_max)
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.order_by('-created_at')

