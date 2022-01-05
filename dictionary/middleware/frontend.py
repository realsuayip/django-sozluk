from django.utils import timezone

from user_agents import parse

from dictionary.utils import get_theme_from_cookie
from dictionary.utils.context_processors import lf_proxy


class MobileDetectionMiddleware:
    # Simple middleware to detect if the user is using a mobile device.
    def __init__(self, get_response):
        self.get_response = get_response  # One-time configuration and initialization.

    def __call__(self, request):
        if request.user.is_authenticated:
            theme = request.user.theme
        else:
            theme = get_theme_from_cookie(request)

        ua_string = request.headers.get("User-Agent", "")
        user_agent = parse(ua_string)

        request.is_mobile = user_agent.is_mobile
        request.theme = theme

        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)

        if request.user.is_authenticated and get_theme_from_cookie(request) != theme:
            response.set_cookie("theme", theme, samesite="Lax", expires=timezone.now() + timezone.timedelta(days=90))

        # Code to be executed for each request/response after
        # the view is called.
        return response


class LeftFrameMiddleware:
    """Injects left frame to context data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_template_response(self, request, response):
        response.context_data["left_frame"] = lf_proxy(request, response) if not request.is_mobile else {}
        return response
