from django.urls import include, path, re_path
from rest_framework import routers
from rest_framework_simplejwt.views import (  
    TokenBlacklistView,
    TokenRefreshView,
    TokenVerifyView
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView,SpectacularRedocView

from fastest_exchange.views import (
                                    SendOtpView,
                                    SignupView,
                                    CreatePasswordView,
                                    CompleteSignupView,
                                    CreatePinView,
                                    LoginView,
                                    VerifyOtpView,
                                   
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

    # Dashboard URLs
    
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
    path('send-otp/', SendOtpView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),
    # path("api/user", views.UserProfileView.as_view(), name="user"),
    
   
    
   
    
]
urlpatterns += [
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("schema/swagger-ui/", SpectacularSwaggerView.as_view(), name="swagger-ui"),
    path("schema/redoc/", SpectacularRedocView.as_view(), name="redoc"),
]

# handler500 = "rest_framework.exceptions.server_error"
# handler400 = "rest_framework.exceptions.bad_request"
