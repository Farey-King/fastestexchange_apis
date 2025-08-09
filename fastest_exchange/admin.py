from django.contrib import admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import (
    VerificationCode,
    BankTransfer,
    ReceiveCash,
    User,
    CompleteSignup,
    Signup,
    CreatePassword,
    CreatePin,
    ExchangeRate,
    Login,
    TransactionHistory,
    TransactionDownload,
    MobileMoney,
    PhoneNumber,
    SwapEngine,
)

# ✅ Custom User change form
class GandariaUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

# ✅ Custom User admin
class GandariaUserAdmin(BaseUserAdmin):
    form = GandariaUserChangeForm
    add_form = UserCreationForm  # Use Django’s default add form (or define your own if you want)

    # ✅ The fields to be used in displaying the User model.
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Office info'), {'fields': ('office',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

# ✅ Make sure it’s not double-registered
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

# admin.site.register(User, GandariaUserAdmin)


@admin.register(TransactionHistory)
class TransactionHistoryAdmin(admin.ModelAdmin):
    list_display = ('reason', 'beneficiary', 'amount', 'date', 'status')
    search_fields = ('reason', 'beneficiary', 'status')
    list_filter = ('status', 'date')

# @admin.register(Swap)
# class SwapAdmin(admin.ModelAdmin):
#     list_display = ['from_currency', 'to_currency', 'amount_sent', 'exchange_rate', 'converted_amount']
#     search_fields = ['user__email', 'from_currency', 'to_currency']
#     list_filter = ['from_currency', 'to_currency']




@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ['currency_from', 'currency_to', 'rate', 'low_amount', 'low_amount_limit']
    search_fields = ['currency_from', 'currency_to']

@admin.register(TransactionDownload)
class TransactionDownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'filename', 'downloaded_at')
    search_fields = ('user__email', 'filename')
    list_filter = ('downloaded_at',)

@admin.register(BankTransfer)
class BankTransferAdmin(admin.ModelAdmin):
    list_display = ('user',
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
                    'created_at')
    search_fields = ('bank', 'account_number', 'account_name')

@admin.register(MobileMoney)
class MobileMoneyAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'amount_sent',
        'currency_from',
        'amount_received',
        'currency_to',
        'agent',
        'receiver_name',
        'receiver_number',
        'narration',
        'status',
        'created_at',
        'proof_of_payment',  # <-- See file link
    )
    search_fields = ('user__email', 'receiver_name', 'receiver_number')
    list_filter = ('status', 'currency_from', 'currency_to', 'created_at')

@admin.register(ReceiveCash)
class ReceiveCashAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount_sent', 'currency_from', 'amount_received', 'currency_to', 'status', 'created_at']
    search_fields = ['user__email', 'receiver_name', 'receiver_phone_number']
    list_filter = ['status', 'currency_from', 'currency_to']



admin.site.register(Signup)
admin.site.register(CreatePassword)
admin.site.register(CompleteSignup)
admin.site.register(CreatePin)
admin.site.register(Login)
admin.site.register(PhoneNumber)
# admin.site.register(SwapEngine)
@admin.register(SwapEngine)
class SwapEngineAdmin(admin.ModelAdmin):
    list_display = ("id", "currency_from", "currency_to", "amount_sent", "exchange_rate", "status", "created_at")
    list_filter = ("status", "currency_from", "currency_to")
    search_fields = ("id", "receiver_account_name", "receiver_account_number")
    actions = ["verify_selected_transactions"]

    def verify_selected_transactions(self, request, queryset):
        updated = queryset.filter(status="pending_verification").update(status="verified")
        self.message_user(request, f"{updated} transaction(s) successfully verified.")
    verify_selected_transactions.short_description = "Mark selected transactions as verified"

@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'created_at')
    search_fields = ('user__email', 'code')
    list_filter = ('created_at',)




