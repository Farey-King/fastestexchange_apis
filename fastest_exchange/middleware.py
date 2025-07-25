import threading
from ast import Dict
from typing import TypedDict

from django.http import HttpRequest
from django.utils import timezone
from user_agents import parse

from .models import Profile, User


class UpdateLastActivityMiddleware(object):

    def __init__(self, get_response):

        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, "user"):
            raise RuntimeError(
                "The UpdateLastActivityMiddleware requires authentication middleware to be installed."
            )

        response = self.get_response(request)

        member: User = request.user
        if member.is_authenticated:
            User.objects.filter(id=member.id).update(last_login=timezone.now())
        return response


# Create a thread-local object
_thread_locals = threading.local()


class UserAgentInfo(TypedDict):
    os: str
    browser: str
    device: str


class RequestUpgrade(HttpRequest):
    user_agent_info: UserAgentInfo = None


def get_current_request() -> RequestUpgrade:
    """Returns the current request object from the thread-local storage."""
    return getattr(_thread_locals, "request", None)


class RequestMiddleware:
    """Middleware that stores the request object in thread-local storage."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        _thread_locals.request = request

        # Parse the User-Agent string
        user_agent = parse(request.META.get("HTTP_USER_AGENT", ""))
        request.user_agent_info = {
            "os": user_agent.os.family,
            "browser": user_agent.browser.family,
            "device": user_agent.device.family,
        }

        response = self.get_response(request)
        return response
