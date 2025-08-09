from http import client
from typing import Dict
from urllib import request

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password,check_password
from django.contrib.auth.signals import user_logged_in
from rest_framework import exceptions, serializers
from rest_framework.pagination import LimitOffsetPagination
from rest_framework_simplejwt.serializers import (
    PasswordField,
    TokenObtainPairSerializer,
)
from django.contrib.auth.models import Permission, Group
from rest_framework_simplejwt.settings import api_settings
from django.utils import timezone
from datetime import timedelta
import random
import string


from .models import (
    TransactionHistory,
    User,
    Signup,
    CompleteSignup,
    CreatePassword,
    CreatePin,
    SwapEngine,
    DeliveryMethod,
    PayoutDetail, 
    # Referral,
    ExchangeRate,
    Login,  # Import for Login model
    PhoneNumber,  # Import for PhoneNumber model

    BankTransfer,
    MobileMoney,
    ReceiveCash,
   
)

# serializers.py
from rest_framework import serializers

class SignupSerializer(serializers.Serializer):
    email = serializers.EmailField()

#phone number serializer
from .utils import generate_otp

class SendOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)

    def validate(self, data):
        phone = data.get("phone_number")
        otp = generate_otp()

        obj, _ = PhoneNumber.objects.update_or_create(
            phone_number=phone,
            defaults={'otp_code': otp, 'otp_created_at': timezone.now()}
        )

        # TODO: Integrate your SMS provider here
        print(f"[DEBUG] Generated and stored OTP {otp} for {phone}")
        
        # Store OTP in data for further processing
        data['generated_otp'] = otp
        return data
# OTP verification serializer
class VerifyOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        phone = data['phone_number']
        otp = data['otp']

        try:
            record = PhoneNumber.objects.get(phone_number=phone, otp_code=otp)
            if record.is_expired():
                raise serializers.ValidationError("OTP has expired.")
            record.is_verified = True
            record.save()
        except PhoneNumber.DoesNotExist:
            raise serializers.ValidationError("Invalid OTP or phone number.")

        return data

    
    


# serializers.py
class CreatePasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data
      

# serializers.py
class CompleteSignupSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone_number = serializers.CharField()
    country = serializers.CharField()
    date_of_birth = serializers.DateField()
    residential_area_1 = serializers.CharField()
    residential_area_2 = serializers.CharField()
    area = serializers.CharField()
    town_city = serializers.CharField()
    occupation = serializers.CharField()
    postal_code = serializers.CharField()


# serializers.py
class CreatePinSerializer(serializers.Serializer):
    # email = serializers.EmailField()
    pin = serializers.CharField(write_only=True, min_length=4, max_length=4)
    pin_confirm = serializers.CharField(write_only=True, min_length=4, max_length=4)

    def validate(self, data):
        if data['pin'] != data['pin_confirm']:
            raise serializers.ValidationError("PINs do not match.")
        return data

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class TransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionHistory
        fields = ['reason', 'beneficiary', 'amount', 'date', 'status']


class PINSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=4, write_only=True)
    
    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain only digits")
        return value

class SwapSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwapEngine
        fields = ['id', 'user', 'from_currency', 'to_currency', 'amount_sent', 'exchange_rate', 'converted_amount', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
   

class ReceiveCashSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiveCash
        fields = '__all__'

class BankTransferSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankTransfer
        fields = ['id',
                  "user",
                  'amount_sent',
                  'currency_from',
                  'amount_received',
                  'currency_to',
                  'agent',
                  'receiver_account_name',
                  'receiver_account_number',
                  'receiver_bank',
                  'narration',
                  'proof_of_payment',
                  'status',
                  'created_at']


class MobileMoneySerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileMoney
        fields = [
            'id',
            'user',
            'amount_sent',
            'currency_from',
            'amount_received',
            'currency_to',
            'agent',
            'receiver_name',
            'receiver_number',
            'narration',
            'proof_of_payment',  # <-- NEW
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'user', 'status', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SwapSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwapEngine
        fields = [
            "currency_from", "currency_to", "amount_sent",
            "exchange_rate", "receiver_account_name",
            "receiver_account_number", "receiver_bank", "converted_amount",
            "payment_method", "verification_mode", "status", "proof_of_payment",
        ]
        read_only_fields = ["converted_amount","verification_mode","proof_of_payment"]  # hides it from Swagger input

    def validate(self, data):
        amount_sent = data.get("amount_sent")
        exchange_rate = data.get("exchange_rate")

        if amount_sent is None or amount_sent <= 0:
            raise serializers.ValidationError("Amount sent must be greater than zero.")
        if exchange_rate is None or exchange_rate <= 0:
            raise serializers.ValidationError("Exchange rate must be greater than zero.")

        data["converted_amount"] = amount_sent * exchange_rate
        return data



class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = [
            # 'id',
            'currency_from',
            'currency_to',
            'low_amount',
            'low_amount_limit',
            'rate',
           
        ]

class VerificationCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    verify_email = serializers.ChoiceField(choices=[('email', 'Email'), ('sms', 'SMS')])

class ApiSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)




class BaseUserSerializer(ApiSerializer):
   
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_login",
            "last_name",
            "profile",
            "notification",
        ]


class BaseProfileSerializer(ApiSerializer):
    # avatar = serializers.ImageField(use_url=False)

    pin = serializers.CharField(write_only=True, required=False)  # Add your pin field

   



class UserSerializer(BaseUserSerializer):
    profile = BaseProfileSerializer()
    class Meta:
        model = User
        # fields = '__all__'
        fields = [
            "date_joined",
            "email",
            "first_name",
            "groups",
            # "office",
            "id",
            "is_active",
            "is_staff",
            "is_superuser",
            "last_login",
            "last_name",
            "url",
            "user_permissions",
            
            "profile",
            "created_by",
            # "updated_by",
        ]

    

class UserRegisterSerializer(UserSerializer):
    profile = BaseProfileSerializer()
    referral_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        read_only=False,
        help_text="Referral code of the referring user",
    )

    class Meta(UserSerializer.Meta):
        fields = [
            "email",
            "first_name",
            "groups",
            # "office",
            "id",
            "last_name",
            "url",
            "username",
            # "profile",
            "password",
            "referral_code",
        ]
        extra_kwargs = {"password": {"write_only": True}}


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super(serializers.Serializer, self).__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField()
        data: dict = kwargs["data"]
        if data.get("pin"):
            self.fields["pin"] = serializers.CharField()
        else:
            self.fields["password"] = PasswordField()

    def validate(self, attrs):
        data = self.do_validate(attrs)

        refresh = self.get_token(self.user)
        if self.user:
            user_logged_in.send(
                sender=self.user.__class__,
                request=self.context["request"],
                user=self.user,
            )

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        return data

    def do_validate(self, attrs: Dict):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
        }
        use_security_pin = attrs.get("pin") is not None
        if use_security_pin:
            authenticate_kwargs["pin"] = int(attrs["pin"])
        else:
            authenticate_kwargs["password"] = attrs["password"]

        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)

        if not api_settings.USER_AUTHENTICATION_RULE(self.user):
            raise exceptions.AuthenticationFailed(
                self.error_messages["no_active_account"],
                "no_active_account",
            )

        return {}

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims

        token["email"] = user.email
        token["id"] = user.id

        return token


