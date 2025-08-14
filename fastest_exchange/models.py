from django.db import models
import os
from random import choice
from turtle import mode
import datetime
from django.contrib.auth.models import AbstractUser, PermissionsMixin,BaseUserManager
from django.contrib.auth.hashers import make_password, check_password

from django.db import models, transaction
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from PIL import Image
from pyexpat import model
from rest_framework_simplejwt.models import TokenUser
from django.core.validators import RegexValidator
from django.conf import settings
from django.contrib.auth import get_user_model





class Signup(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
class PhoneNumber(models.Model):
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    termii_message_id = models.CharField(max_length=100, null=True, blank=True)  # Optional: if Termii provides one
    attempts = models.IntegerField(default=0)  # 

    
    def is_expired(self):
        if self.otp_created_at is None:
            return True  # Consider it expired if no timestamp exists
        return timezone.now() > self.otp_created_at + datetime.timedelta(minutes=5)

    def __str__(self):
        return f"{self.phone_number} - {self.otp_code} - {self.otp_created_at}"

    
class CreatePassword(models.Model):
    password = models.CharField(max_length=255)
    password_confirm = models.CharField(max_length=255)

    def __str__(self):
        return f"Password for {self.password} and confirmation {self.password_confirm}"

class CompleteSignup(models.Model):
    email = models.EmailField()
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=15)
    country = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    residential_area_1 = models.CharField(max_length=100)
    residential_area_2 = models.CharField(max_length=100)
    area = models.CharField(max_length=100)
    town_city = models.CharField(max_length=100)
    occupation = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

class CreatePin(models.Model):

    pin = models.CharField(max_length=4)


    def __str__(self):
        return f"PIN: {self.pin}"


class Login(models.Model):
    email = models.EmailField()
    password = models.CharField(max_length=255, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Login for {self.email} with password {self.password}"
    
# models.py

class SwapEngine(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ("bank_transfer", "Bank Transfer"),
        ("mobile_money", "Mobile Money"),
        ("cash", "Cash"),
    ]

    CURRENCY_CHOICES = [
        ("UGX", "Ugandan Shilling"),
        ("NGN", "Nigerian Naira"),
        ("USD", "US Dollar"),
    ]

    VERIFICATION_MODE_CHOICES = [
        ("manual", "Manual"),
        ("automated", "Automated"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("failed", "Failed"),
    ]
    # user = models.ForeignKey(Login, on_delete=models.CASCADE)
    currency_from = models.CharField(max_length=10)
    currency_to = models.CharField(max_length=10)
    amount_sent = models.DecimalField(max_digits=12, decimal_places=2)
    converted_amount = models.DecimalField(max_digits=12, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=6) 
    receiver_account_name = models.CharField(max_length=100)
    receiver_account_number = models.CharField(max_length=100)
    receiver_bank = models.CharField(max_length=100)  # <-- Snapshot!
    created_at = models.DateTimeField(auto_now_add=True)

      # New fields for payment integration
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    verification_mode = models.CharField(max_length=20, choices=VERIFICATION_MODE_CHOICES, default="manual")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Optional: store proof of payment if user uploads it
    proof_of_payment = models.FileField(upload_to="payment_proofs/", blank=True, null=True)
    provider_transaction_id = models.CharField(max_length=100, blank=True, null=True)  # For automated mode

    def __str__(self):
        return f"{self.amount_sent} {self.currency_from} to {self.currency_to} at {self.exchange_rate}"
    

class SavedBeneficiary(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_beneficiaries"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")

    # Link to saved beneficiary (optional)
    beneficiary = models.ForeignKey(
        "Beneficiary",
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    # Manual beneficiary fields
    beneficiary_full_name = models.CharField(max_length=255, blank=True, null=True)
    beneficiary_country = models.CharField(max_length=100, blank=True, null=True)
    beneficiary_delivery_method = models.CharField(max_length=20, blank=True, null=True)
    beneficiary_account_number = models.CharField(max_length=100, blank=True, null=True)
    beneficiary_currency = models.CharField(max_length=10, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.id} - {self.status}"



class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser, PermissionsMixin):
    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")],
        blank=True,
        null=True
    )
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)
    pin = models.CharField(max_length=255, blank=True, null=True)  # Store hashed PIN
    pin_attempts = models.IntegerField(default=0)
    pin_locked_until = models.DateTimeField(blank=True, null=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)  # For SMS OTP
    otp_created_at = models.DateTimeField(blank=True, null=True)  # OTP timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix the conflicts by adding related_name
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='fastest_exchange_users',
        related_query_name='fastest_exchange_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='fastest_exchange_users',
        related_query_name='fastest_exchange_user',
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    

class Swap(models.Model):
    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    from_currency = models.CharField(max_length=10)
    to_currency = models.CharField(max_length=10)
    amount_sent = models.DecimalField(max_digits=12, decimal_places=2)
    exchange_rate = models.DecimalField(max_digits=12, decimal_places=2)
    converted_amount = models.DecimalField(max_digits=12, decimal_places=2)
    # created_at = models.DateTimeField(auto_now_add=True)


class AccountSettings(models.Model):
    user = models.OneToOneField(CompleteSignup, on_delete=models.CASCADE)
    phone = models.CharField(max_length=30, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    city_state = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} Account Settings"

class DeliveryMethod(models.Model):
    METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('cash', 'Cash Pickup'),
    ]
    method = models.CharField(max_length=50, choices=METHOD_CHOICES, unique=True)
    name = models.CharField(max_length=100)

class PayoutDetail(models.Model):
    swap = models.ForeignKey(Swap, on_delete=models.CASCADE, related_name='payout_details')
    method = models.CharField(max_length=50)  # bank_transfer, mobile_money, cash
    details = models.JSONField()

# class Referral(models.Model):
#     user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
#     code = models.CharField(max_length=10, unique=True)
#     referred_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='referred_by')
#     bonus_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)

# class ExchangeRate(models.Model):
#     from_currency = models.CharField(max_length=10)
#     to_currency = models.CharField(max_length=10)
#     rate = models.DecimalField(max_digits=12, decimal_places=2)
#     updated_at = models.DateTimeField(auto_now=True)
#     def set_pin(self, raw_pin):
        
#         self.pin = make_password(raw_pin)
        

#     def check_pin(self, pin):
#         if not self.pin:
#             return False
#         return check_password(pin, self.pin)

# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
#     first_name = models.CharField(max_length=30, blank=True)
#     last_name = models.CharField(max_length=30, blank=True)
#     date_of_birth = models.DateField(blank=True, null=True)
#     profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
class VerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    code_type = models.CharField(max_length=10, choices=[('email', 'Email'), ('sms', 'SMS')])
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    
    def is_expired(self):
        return timezone.now() > self.expires_at


class CreateOnlyModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(class)s_created_by",
    )

    class Meta:
        abstract = True
        ordering = ("-id",)
        get_latest_by = "created_at"


class EditableModel(CreateOnlyModel):
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(class)s_updated_by",
    )

    class Meta:
        abstract = True


class AcceptableModel(CreateOnlyModel):
    accepted_at = models.DateTimeField(blank=True, null=True)
    accepted_by = models.ForeignKey(
        "User",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="%(class)s_accepted_by",
    )

    class Meta:
        abstract = True



    def check_pin(self, pin):
        return self.profile.pin == pin


def get_media_upload_path(instance, filename):
    return os.path.join(
        "profile_images", "user_%d" % instance.user.id, "avatar_%s" % filename
    )

class IDVerification(models.Model):
    COUNTRY_CHOICES = [
        ('UG', 'Uganda'),
        ('KE', 'Kenya'),
        ('TZ', 'Tanzania'),
        ('RW', 'Rwanda'),
        ('SS', 'South Sudan'),
        ('ZM', 'Zambia'),
        ('MW', 'Malawi'),
        ('NG', 'Nigeria'),
        ('GH', 'Ghana'),
        ('ET', 'Ethiopia'),
        ('ZA', 'South Africa'),
        ('BW', 'Botswana'),
        ('NA', 'Namibia'),
        ('ZW', 'Zimbabwe'),
        ('MW', 'Malawi'),
        ('CM', 'Cameroon'),
        ('CI', 'Côte d\'Ivoire'),
    ]

    DOCUMENT_CHOICES = [
        ('voter_id', 'Voter ID'),
        ('passport', 'International Passport'),
        ('driver_license', 'Driver\'s License'),
        ('national_id', 'National ID'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    country = models.CharField(max_length=50, choices=COUNTRY_CHOICES)
    document_type = models.CharField(max_length=20,  choices=DOCUMENT_CHOICES)
    id_number = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.document_type}"

class Profile(models.Model):
    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=get_media_upload_path, blank=True, null=True)
    bio = models.TextField(null=True, blank=True)
    pin = models.IntegerField(null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    phone_number = PhoneNumberField(null=True, blank=True, default=None)
    address = models.TextField(max_length=150, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=2)

    # resizing images
    # def save(self, *args, **kwargs):
    #     super().save()
    #     # TODO: Generate thumbnail
    #     if self.avatar:
    #         img = Image.open(self.avatar.path)

    #     if img and (img.height > 100 or img.width > 100):
    #         new_img = (100, 100)
    #         img.thumbnail(new_img)
    #         img.save(self.avatar.path)

    # def __str__(self):
    #     return "Profile: " + self.user.username


class Office(EditableModel):
    name = models.CharField(max_length=120)
    address = models.TextField(max_length=200, null=True, blank=True)
    country = models.CharField(max_length=20)
    city = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.name


class Person(EditableModel):
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    birthday = models.DateField(null=True, blank=True)
    email = models.EmailField(_("email address"), blank=True, null=True)
    phone_number = PhoneNumberField(unique=True, null=True, blank=True)
    address = models.CharField(max_length=150)
    city = models.CharField(max_length=50)
    country = models.CharField(max_length=2)

    class Meta(EditableModel.Meta):
        abstract = True


class Notification(models.Model):
    user = models.OneToOneField(
        User, related_name="notification", on_delete=models.CASCADE
    )
    fx_rate = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(
                fields=["fx_rate"],
                name="notice_fx_rate_idx",
                condition=models.Q(fx_rate=True),
            ),
        ]


class ClientAccount(EditableModel):
    id = models.IntegerField(primary_key=True)
    owner = models.OneToOneField(User, related_name="account", on_delete=models.CASCADE)

    def __str__(self):
        return "Acoount: %s %s " % (self.owner.first_name, self.owner.last_name)


class AccountType(models.TextChoices):
    BANK = "bank"
    MOBILE_MONEY = "mobile_money"
    CRYPTO = "crypto"
    WALLET = "wallet"


class PaymentMethod(EditableModel):

    name = models.CharField(max_length=255)
    type = models.CharField(choices=AccountType.choices, max_length=50)

    def __str__(self):
        return "PaymentMethod: %s" % (self.name.first_name)


class Beneficiary(Person):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="beneficiaries",  # This creates a reverse relation 'user.beneficiaries'
    )
    name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=255, blank=True, null=True)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.RESTRICT, related_name="beneficiaries"
    )
    account_number = models.IntegerField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    country = models.CharField(max_length=2)

    def __str__(self):
        return "Account: %s %s " % (self.owner.first_name, self.owner.last_name)


# class Client(Person):
#     """Client Account"""

#     receive_price_update = models.BooleanField(default=False)

#     def __str__(self):
#         return "%s %s" % (self.first_name, self.last_name)

#     class Meta:
#         indexes = [
#             models.Index(
#                 fields=["receive_price_update"],
#                 name="receive_price_update_idx",
#                 condition=models.Q(receive_price_update=True),
#             ),
#         ]


class Currency(models.TextChoices):
    BWP = "BWP"
    RMB = "RMB"
    ETB = "ETB"
    GHC = "GHC"
    KES = "KES"
    MWK = "MWK"
    NAD = "NAD"
    NGN = "NGN"
    RWF = "RWF"
    ZAR = "ZAR"
    SSP = "SSP"
    TZS = "TZS"
    UGX = "UGX"
    AED = "AED"
    GBP = "GBP"
    USD = "USD"
    XAF = "XAF"
    BTC = "BTC"
    USDT = "USDT"
    USDC = "USDC"


class OperatingAccount(EditableModel):
    class Type(models.IntegerChoices):
        BANK = 1
        MOBILE_PAYMENT = 2
        CRYPTO = 3
        CASH = 4

    name = models.CharField(max_length=20, null=True, blank=True)
    type = models.IntegerField(choices=Type.choices)
    currency = models.CharField(choices=Currency.choices, max_length=5)
    office = models.ForeignKey(Office, on_delete=models.PROTECT)
    # balance = models.DecimalField(max_digits=20, decimal_places=8, default=0)

    # @property
    # def total_credit(self):
    #     return self.transactions.filter(type=1).aggregate(models.Sum('amount'))['amount_sum']

    # @property
    # def balance(self):
    #     total_credit = models.functions.Coalesce(models.Sum('amount', filter=models.Q(type=1), output_field=models.FloatField()), 0.00)
    #     total_debit = models.functions.Coalesce(models.Sum('amount', filter=models.Q(type=2), output_field=models.FloatField()), 0.00)
    #     total = self.transactions.aggregate(balance=total_credit - total_debit)['balance']
    #     return total

    def __str__(self):
        return "%s Operating Account - %s" % (self.office, self.Type(self.type).name)





# class ExchangeRate(EditableModel):
#     currency_pair = models.CharField(choices=CurrencyPair.choices, max_length=10)
#     buy = models.DecimalField(max_digits=20, decimal_places=8)
#     sell = models.DecimalField(max_digits=20, decimal_places=8)

#     def __str__(self) -> str:
#         return "%s: B:%.2f S:%.2f" % (self.currency_pair.replace('_', "/"), self.buy, self.sell)


class ExchangeRate(models.Model):
    currency_from = models.CharField(choices=Currency.choices, max_length=10)
    currency_to = models.CharField(choices=Currency.choices, max_length=10)
    low_amount = models.DecimalField(
        max_digits=32, decimal_places=8, null=True, blank=True
    )
    low_amount_limit = models.DecimalField(
        max_digits=32, decimal_places=19, null=True, blank=True
    )
    rate = models.DecimalField(max_digits=32, decimal_places=19)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return "%s to %s @%.2f" % (self.currency_from, self.currency_to, self.rate)

class TransactionHistory(models.Model):
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]

    reason = models.CharField(max_length=255)
    beneficiary = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return f"{self.reason} - {self.beneficiary} - {self.status}"

User = get_user_model()

class TransactionDownload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=255, default="transactions.csv")
    # Optionally: save extra context (date range, filters)
    note = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} downloaded {self.filename} at {self.downloaded_at}"

class BankTransfer(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    amount_sent = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_from = models.CharField(max_length=10, default='USD')
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_to = models.CharField(max_length=10, default='UGX  ')
    agent = models.CharField(max_length=255, blank=True, null=True)
    receiver_account_name = models.CharField(max_length=255, blank=True, null=True)
    receiver_account_number = models.CharField(max_length=50, blank=True, null=True)
    receiver_bank = models.CharField(max_length=255, blank=True, null=True)
    narration = models.TextField(blank=True, null=True)
    proof_of_payment = models.FileField(upload_to='proofs/', blank=True, null=True)  # <-- NEW
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    bank = models.CharField(max_length=255)
    account_number = models.CharField(max_length=50)
    account_name = models.CharField(max_length=255)
    narration = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bank} - {self.account_number} - {self.account_name}"

class MobileMoney(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    amount_sent = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_from = models.CharField(max_length=10, default='USD')
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_to = models.CharField(max_length=10, default='UGX')
    agent = models.CharField(max_length=255, blank=True, null=True)
    receiver_name = models.CharField(max_length=255, blank=True, null=True)
    receiver_number = models.CharField(max_length=50, blank=True, null=True)
    narration = models.TextField(blank=True, null=True)
    proof_of_payment = models.FileField(upload_to='proofs/', blank=True, null=True)  # <-- NEW
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.amount_sent} {self.currency_from} to {self.currency_to} - {self.status}"

class ReceiveCash(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    amount_sent = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_from = models.CharField(max_length=10, default='USD')
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_to = models.CharField(max_length=10, default='UGX')
    agent = models.CharField(max_length=255, blank=True, null=True)
    receiver_name = models.CharField(max_length=255, blank=True, null=True)
    receiver_IDnumber = models.CharField(max_length=50, blank=True, null=True)
    receiver_phone_number = models.CharField(max_length=50, blank=True, null=True)
    narration = models.TextField(blank=True, null=True)
    proof_of_payment = models.FileField(upload_to='proofs/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('successful', 'Successful')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.amount_sent} {self.currency_from} - {self.status}"


class DocumentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"


class KYC(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    bvn_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_number_verified = models.BooleanField(default=False)
    national_identity_verified = models.BooleanField(default=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="kyc")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='kyc_reviews')
    reviewer_notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"KYC for {self.user.username} - {self.status}"


def get_kyc_upload_path(instance, filename):
    return os.path.join(
        "kyc_documents", "user_%d" % instance.user.id, "avatar_%s" % filename
    )


class IdentityDocumentType(models.TextChoices):
    BVN = "BVN", "Bank Verification Number"
    PASSPORT = "PASSPORT", "Passport"
    ID_CARD = "ID_CARD", "National ID Card"
    RESIDENT_CARD = "RESIDENT_CARD", "Resident Card"
    DRIVER_LICENSE = "DRIVER_LICENSE", "Driver License"


class IdentityDocument(models.Model):
    kyc = models.ForeignKey(KYC, on_delete=models.CASCADE, related_name="documents")
    document_type = models.CharField(
        max_length=50,
        choices=IdentityDocumentType.choices,
    )
    document_file = models.FileField(
        upload_to=get_kyc_upload_path, blank=True, null=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    document_number = models.CharField(max_length=50, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )

    def __str__(self):
        return f"{self.document_type} for {self.kyc.user.username}"


class Request(AcceptableModel):
    class ModelType(models.IntegerChoices):
        TRANSACTION = 1
        CLIENT = 2

    type = models.IntegerField(choices=ModelType.choices)
    object_id = models.BigIntegerField()
    data = models.JSONField()
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["type", "object_id"],
                condition=models.Q(is_active=True),
                name="unique_request",
            )
        ]

    def __str__(self) -> str:
        return "ModReq #%s" % (self.id)


class PasswordReset(models.Model):
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
    )
    token = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral")
    referred_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals"
    )
    referral_code = models.CharField(max_length=20, unique=True)
    commission = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} referred by {self.referred_by.username if self.referred_by else 'None'}"

    def generate_referral_code(self):
        """Generate a unique referral code for the user."""
        import uuid

        self.referral_code = str(uuid.uuid4())[:8].upper()
        self.save()


class Reward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rewards")
    points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.points} points"

# Create your models here.

# Transaction Engine Models
class TransactionType(models.TextChoices):
    SWAP = "SWAP", "Currency Swap"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
    MOBILE_MONEY = "MOBILE_MONEY", "Mobile Money"
    CASH_PICKUP = "CASH_PICKUP", "Cash Pickup"
    KYC_SUBMISSION = "KYC_SUBMISSION", "KYC Submission"
    BENEFICIARY_MANAGEMENT = "BENEFICIARY_MANAGEMENT", "Beneficiary Management"

class TransactionStatus(models.TextChoices):
    INITIATED = "INITIATED", "Initiated"
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    REQUIRES_VERIFICATION = "REQUIRES_VERIFICATION", "Requires Verification"
    VERIFIED = "VERIFIED", "Verified"

class Transaction(models.Model):
    """Core Transaction model for tracking all transactions in the system"""
    
    # Unique transaction identifier
    transaction_id = models.CharField(max_length=32, unique=True, db_index=True)
    
    # User who initiated the transaction
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='transactions'
    )
    
    # Transaction details
    transaction_type = models.CharField(
        max_length=30, 
        choices=TransactionType.choices
    )
    status = models.CharField(
        max_length=25, 
        choices=TransactionStatus.choices, 
        default=TransactionStatus.INITIATED
    )
    
    # Financial details
    amount_sent = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    currency_from = models.CharField(max_length=10, blank=True, null=True)
    amount_received = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    currency_to = models.CharField(max_length=10, blank=True, null=True)
    exchange_rate = models.DecimalField(
        max_digits=15, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    
    # Reference to specific transaction models
    swap_reference = models.ForeignKey(
        'SwapEngine', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    bank_transfer_reference = models.ForeignKey(
        'BankTransfer', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    mobile_money_reference = models.ForeignKey(
        'MobileMoney', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    cash_pickup_reference = models.ForeignKey(
        'ReceiveCash', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    kyc_reference = models.ForeignKey(
        'KYC', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    beneficiary_reference = models.ForeignKey(
        'SavedBeneficiary', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking fields
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.transaction_id} - {self.transaction_type} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
    
    def generate_transaction_id(self):
        """Generate a unique transaction ID"""
        import uuid
        import time
        
        # Format: TXN + timestamp + random
        timestamp = str(int(time.time()))[-8:]  # Last 8 digits of timestamp
        random_part = str(uuid.uuid4()).replace('-', '')[:8].upper()
        return f"TXN{timestamp}{random_part}"
    
    def mark_completed(self):
        """Mark transaction as completed"""
        self.status = TransactionStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save()
    
    def mark_failed(self, reason=None):
        """Mark transaction as failed"""
        self.status = TransactionStatus.FAILED
        if reason:
            self.notes = f"{self.notes or ''}\nFailed: {reason}"
        self.save()

class TransactionStatusHistory(models.Model):
    """Track status changes for transactions"""
    
    transaction = models.ForeignKey(
        Transaction, 
        on_delete=models.CASCADE, 
        related_name='status_history'
    )
    
    old_status = models.CharField(
        max_length=25, 
        choices=TransactionStatus.choices,
        null=True,
        blank=True
    )
    new_status = models.CharField(
        max_length=25, 
        choices=TransactionStatus.choices
    )
    
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    reason = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Transaction Status Histories"
    
    def __str__(self):
        return f"{self.transaction.transaction_id}: {self.old_status} → {self.new_status}"
