from django.shortcuts import render

# Create your views here.
import os
from datetime import datetime, timedelta
from typing import Dict, List, Type

from django.contrib.auth import update_session_auth_hash, get_user_model, authenticate
from django.db import IntegrityError 
from django.db import models 
from django.db.models import ProtectedError 
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse 


# To bypass having a CSRF token
# from django_renderpdf.views import PDFView  # Removed due to unresolved import
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token 
from rest_framework.authtoken.views import ObtainAuthToken 
from rest_framework.decorators import action, api_view, permission_classes 
from rest_framework.permissions import AllowAny 
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
   
)

from .serializers import (
   
    MyTokenObtainPairSerializer,
   
     # Added import for UserLoginSerializer
    PINSerializer,  # Added import for PINSerializer
    VerificationCodeSerializer,  # Added import for VerificationCodeSerializer
    SignupSerializer,  # Added import for SignupSerializer
    
    CreatePasswordSerializer,  # Added import for CreatePasswordSerializer
    CompleteSignupSerializer,  # Added import for CompleteProfileSerializer
    CreatePinSerializer,  # Added import for CreatePinSerializer
    LoginSerializer,  # Added import for LoginSerializer
    SignupSerializer,  # Added import for SignupSerialize
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

        # ✅ Check if a user already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "An account with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ✅ Create inactive user
        user = User.objects.create(email=email, is_active=False)

        # ✅ Generate verification token
        token = str(uuid.uuid4())
        expires_at = timezone.now() + timezone.timedelta(minutes=30)

        VerificationCode.objects.create(
            user=user,
            code=token,
            code_type='email',
            expires_at=expires_at
        )

        # ✅ Build link
        verification_url = (
            f"{settings.FRONTEND_URL}/create-password"
            f"?token={token}&email={email}"
        )

        print(f"Verification URL: {verification_url}")

        # ✅ Send email
        email_message = EmailMessage(
            subject="Verify Your Email",
            body=f"""
Hi,

Thanks for signing up!

Click below to verify your email and set your password:

{verification_url}

This link will expire in 30 minutes.

If you didn't request this, you can ignore this email.

Thanks,
Your fastest.exchange Team
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )
        email_message.send(fail_silently=False)

        return Response(
            {"message": "Verification email sent."},
            status=status.HTTP_201_CREATED
        )



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

        return Response({"message": "Password set. Please complete your profile."})

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
        return Response({"message": "Profile completed. Please set your PIN."})


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
        return Response({"message": "PIN set. Signup complete!"})
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
            "email": user.email,
            "message": "Login successful."
        }, status=status.HTTP_200_OK)



    @csrf_exempt
    def send_verification_code(self, user, code_type):
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

