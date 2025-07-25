# backends.py
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from storages.backends.s3boto3 import S3Boto3Storage

from fastest_exchange.models import User


class PasswordAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, email=None, password=None, **kwargs):
        UserModel = get_user_model()
        username = kwargs.get("username")

        if email is None and username is not None:
            email = username  # Admin login passes username → treat it as email

        if email is None or password is None:
            return None

        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None

        
        if not user.is_active:
            return None
        
        if user.check_password(password):
            return user

    def get_user(self, user_id):
        UserModel = get_user_model()

        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None


class StaticStorage(S3Boto3Storage):
    location = "Fastest/static"
    default_acl = "public-read"


class PublicMediaStorage(S3Boto3Storage):
    location = "Fastest/media"
    default_acl = "public-read"
    file_overwrite = False
