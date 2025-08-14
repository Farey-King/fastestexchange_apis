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
    SavedBeneficiary,
    KYC,
    
    # Transaction Engine models
    Transaction,
    TransactionStatusHistory,
    TransactionType,
    TransactionStatus,
)

# Exchange Rate Serializers
class ExchangeRateSerializer(serializers.ModelSerializer):
    """Serializer for ExchangeRate model"""
    
    class Meta:
        model = ExchangeRate
        fields = ['id', 'currency_from', 'currency_to', 'rate', 'low_amount', 
                 'low_amount_limit', 'created_at']
        read_only_fields = ['id', 'created_at']

class ExchangeRateUpdateSerializer(serializers.Serializer):
    """Serializer for updating exchange rates"""
    
    currency_from = serializers.CharField(max_length=10)
    currency_to = serializers.CharField(max_length=10)
    rate = serializers.DecimalField(max_digits=32, decimal_places=19)
    low_amount = serializers.DecimalField(
        max_digits=32, decimal_places=8, required=False, allow_null=True
    )
    low_amount_limit = serializers.DecimalField(
        max_digits=32, decimal_places=19, required=False, allow_null=True
    )
    
    def validate_currency_from(self, value):
        return value.upper()
    
    def validate_currency_to(self, value):
        return value.upper()
    
    def validate(self, data):
        if data['currency_from'] == data['currency_to']:
            raise serializers.ValidationError(
                "Source and target currencies cannot be the same"
            )
        return data

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

# class SwapSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = SwapEngine
#         fields = ['id', 'user', 'from_currency', 'to_currency', 'amount_sent', 'exchange_rate', 'converted_amount', 'payment_method',  'status', 'created_at']
#         read_only_fields = ['id', 'user', 'status', 'created_at']

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
        read_only_fields = ["converted_amount", "proof_of_payment"]  # hides it from Swagger input

    def validate(self, data):
        amount_sent = data.get("amount_sent")
        exchange_rate = data.get("exchange_rate")

        if amount_sent is None or amount_sent <= 0:
            raise serializers.ValidationError("Amount sent must be greater than zero.")
        if exchange_rate is None or exchange_rate <= 0:
            raise serializers.ValidationError("Exchange rate must be greater than zero.")

        data["converted_amount"] = amount_sent * exchange_rate
        return data


class SavedBeneficiarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedBeneficiary
        fields = "__all__"
        read_only_fields = ["id", "user", "status", "created_at", "exchange_rate"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["user"] = request.user

        beneficiary = validated_data.get("beneficiary")
        if beneficiary:
            # Pull details from saved beneficiary
            validated_data["beneficiary_full_name"] = beneficiary.full_name
            validated_data["beneficiary_country"] = beneficiary.country
            validated_data["beneficiary_delivery_method"] = beneficiary.delivery_method
            validated_data["beneficiary_account_number"] = beneficiary.account_number
            validated_data["beneficiary_currency"] = beneficiary.currency

class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = "__all__"
        read_only_fields = ["status", "submitted_at", "reviewed_at", "reviewed_by"]
    
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

# Transaction Engine Serializers
class TransactionStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for transaction status history"""
    
    changed_by_email = serializers.CharField(source='changed_by.email', read_only=True)
    
    class Meta:
        model = TransactionStatusHistory
        fields = [
            'id', 'old_status', 'new_status', 'changed_by', 'changed_by_email',
            'reason', 'timestamp'
        ]
        read_only_fields = ['id', 'timestamp', 'changed_by_email']

class TransactionSerializer(serializers.ModelSerializer):
    """Main Transaction serializer"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    status_history = TransactionStatusHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'user', 'user_email', 'transaction_type', 
            'status', 'amount_sent', 'currency_from', 'amount_received', 
            'currency_to', 'exchange_rate', 'swap_reference', 'bank_transfer_reference',
            'mobile_money_reference', 'cash_pickup_reference', 'kyc_reference',
            'beneficiary_reference', 'metadata', 'notes', 'created_at', 'updated_at',
            'completed_at', 'ip_address', 'user_agent', 'status_history'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'user_email', 'created_at', 
            'updated_at', 'completed_at', 'status_history'
        ]
    
    def create(self, validated_data):
        """Create a new transaction"""
        request = self.context.get('request')
        if request:
            validated_data['user'] = request.user
            validated_data['ip_address'] = self.get_client_ip(request)
            validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return super().create(validated_data)
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

class TransactionCreateSerializer(serializers.Serializer):
    """Serializer for creating different types of transactions"""
    
    transaction_type = serializers.ChoiceField(
        choices=TransactionType.choices,
        help_text="Type of transaction to create"
    )
    
    # Common fields for financial transactions
    amount_sent = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        required=False,
        help_text="Amount being sent"
    )
    currency_from = serializers.CharField(
        max_length=10, 
        required=False,
        help_text="Source currency code"
    )
    amount_received = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        required=False,
        help_text="Amount to be received"
    )
    currency_to = serializers.CharField(
        max_length=10, 
        required=False,
        help_text="Target currency code"
    )
    exchange_rate = serializers.DecimalField(
        max_digits=15, 
        decimal_places=8, 
        required=False,
        help_text="Exchange rate used"
    )
    
    # Transaction-specific data
    transaction_data = serializers.JSONField(
        required=False,
        help_text="Transaction-specific data (varies by transaction type)"
    )
    
    metadata = serializers.JSONField(
        required=False,
        help_text="Additional metadata for the transaction"
    )
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        help_text="Additional notes for the transaction"
    )
    
    def validate(self, data):
        transaction_type = data.get('transaction_type')
        transaction_data = data.get('transaction_data', {})
        
        # Validate based on transaction type
        if transaction_type in [TransactionType.SWAP, TransactionType.BANK_TRANSFER, 
                               TransactionType.MOBILE_MONEY, TransactionType.CASH_PICKUP]:
            # Financial transactions require amount and currency info
            if not data.get('amount_sent'):
                raise serializers.ValidationError(
                    "amount_sent is required for financial transactions"
                )
            if not data.get('currency_from'):
                raise serializers.ValidationError(
                    "currency_from is required for financial transactions"
                )
        
        return data

class TransactionUpdateStatusSerializer(serializers.Serializer):
    """Serializer for updating transaction status"""
    
    status = serializers.ChoiceField(
        choices=TransactionStatus.choices,
        help_text="New status for the transaction"
    )
    reason = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Reason for status change"
    )
    notes = serializers.CharField(
        max_length=1000,
        required=False,
        help_text="Additional notes"
    )

class TransactionListSerializer(serializers.ModelSerializer):
    """Simplified serializer for transaction lists"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'transaction_id', 'user_email', 'transaction_type', 'status',
            'amount_sent', 'currency_from', 'amount_received', 'currency_to',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = fields

