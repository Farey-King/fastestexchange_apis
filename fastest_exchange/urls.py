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
                                    KYCReviewQueueView,
                                    KYCApproveRejectView,
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
     path("kyc/submit/", KYCSubmissionView.as_view(), name="kyc-submit"),
    path("kyc/review-queue/", KYCReviewQueueView.as_view(), name="kyc-review-queue"),
    path("kyc/review/<int:pk>/", KYCApproveRejectView.as_view(), name="kyc-approve-reject"),

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
