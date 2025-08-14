from django.urls import include, path, re_path
from rest_framework import routers
from rest_framework_simplejwt.views import (  
    TokenBlacklistView,
    TokenRefreshView,
    TokenVerifyView
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView,SpectacularRedocView

from fastest_exchange.views import (
                                    SendOTPView,
                                    SignupView,
                                    CreatePasswordView,
                                    CompleteSignupView,
                                    CreatePinView,
                                    LoginView,
                                    VerifyOTPView,
                                    SwapView,
                                    ManualVerifyView,
                                    SavedBeneficiaryView,
                                    KYCSubmissionView,
                                    
                                    # Transaction Engine views
                                    TransactionCreateView,
                                    TransactionListView,
                                    TransactionDetailView,
                                    TransactionUpdateStatusView,
                                    TransactionStatsView,
                                    TransactionSearchView,
                                    
                                    # KYCReviewQueueView,
                                   )

# Exchange Rate Management views
from fastest_exchange.exchange_rate_views import (
    get_exchange_rate,
    calculate_conversion,
    get_supported_pairs,
    ExchangeRateManagementView,
    ExchangeRateListView,
    get_rate_history,
    refresh_rates_from_apis,
    get_rate_service_config,
)
app_name = "expense_tracker"
# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter(trailing_slash=False)
router.include_root_view = True

urlpatterns = [
    path('api/auth/login', LoginView.as_view(), name='login'),
    path('api/auth/signup', SignupView.as_view(), name='signup'),
    # path('auth/verify-email', EmailVerificationView.as_view(), name='verify-email'),
    path('api/auth/create-password', CreatePasswordView.as_view(), name='create-password'),
    path('api/auth/complete-signup', CompleteSignupView.as_view(), name='complete-signup'),
    path('api/auth/create-pin', CreatePinView.as_view(), name='create-pin'),
    path('phone/request-otp/', SendOTPView.as_view(), name='request-otp'),
    path('phone/verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),

    # Dashboard URLs
    path("api/swap", SwapView.as_view(), name="swap"),
    path("api/verify/manual/<int:transaction_id>/", ManualVerifyView.as_view(), name="manual-verify"),
    path("api/saved-beneficiaries/", SavedBeneficiaryView.as_view(), name="saved-beneficiaries"),
    
    # ==================================================
    # TRANSACTION ENGINE ENDPOINTS
    # ==================================================
    
    # Core transaction management
    path("api/transactions/create/", TransactionCreateView.as_view(), name="transaction-create"),
    path("api/transactions/", TransactionListView.as_view(), name="transaction-list"),
    path("api/transactions/<str:transaction_id>/", TransactionDetailView.as_view(), name="transaction-detail"),
    path("api/transactions/<str:transaction_id>/status/", TransactionUpdateStatusView.as_view(), name="transaction-update-status"),
    
    # Transaction analytics and search
    path("api/transactions/stats/", TransactionStatsView.as_view(), name="transaction-stats"),
    path("api/transactions/search/", TransactionSearchView.as_view(), name="transaction-search"),
    
    # ==================================================
    # EXCHANGE RATE MANAGEMENT ENDPOINTS
    # ==================================================
    
    # Public exchange rate endpoints (anyone can check rates)
    path("api/exchange-rates/get/", get_exchange_rate, name="get-exchange-rate"),
    path("api/exchange-rates/convert/", calculate_conversion, name="calculate-conversion"),
    path("api/exchange-rates/pairs/", get_supported_pairs, name="supported-currency-pairs"),
    
    # Admin-only exchange rate management
    path("api/admin/exchange-rates/update/", ExchangeRateManagementView.as_view(), name="admin-update-rate"),
    path("api/admin/exchange-rates/list/", ExchangeRateListView.as_view(), name="admin-list-rates"),
    path("api/admin/exchange-rates/history/", get_rate_history, name="admin-rate-history"),
    path("api/admin/exchange-rates/refresh/", refresh_rates_from_apis, name="admin-refresh-rates"),
    path("api/admin/exchange-rates/config/", get_rate_service_config, name="admin-rate-config"),
    
    # Auth Token generation
    path("api/", include("rest_framework.urls", namespace="rest_framework")),
    path("api/", include(router.urls)),
    # path(
    #     "api/auth/token",
    #     views.MyTokenObtainPairView.as_view(),
    #     name="token_obtain_pair",
    # ),
    path("api/auth/token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/token/verify", TokenVerifyView.as_view(), name="token_verify"),
    path("api/auth/token/blacklist", TokenBlacklistView.as_view(), name="token_blacklist"),
   
   
    
   
    
]
urlpatterns += [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger-ui/", SpectacularSwaggerView.as_view(), name="swagger-ui"),
    path("schema/redoc/", SpectacularRedocView.as_view(), name="redoc"),
]

# handler500 = "rest_framework.exceptions.server_error"
# handler400 = "rest_framework.exceptions.bad_request"
