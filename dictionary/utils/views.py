from urllib.parse import parse_qsl

from django.conf import settings
from django.contrib import messages as notifications
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import View

from .decorators import require_ajax
from .mixins import IntermediateActionMixin


class IntermediateActionView(PermissionRequiredMixin, IntermediateActionMixin, View):
    pass


class JSONView(View):
    """**DEPRECATED**"""
    http_method_names = ['get', 'post']

    def render_to_json_response(self, data, status=200):
        return JsonResponse(data, status=status)

    def success(self, message="200 OK", status=200):
        return {"success": message}, status

    def error(self, message="500 Internal Server Error", status=500):
        return {"error": message}, status

    def bad_request(self):
        return {"error": "400 Bad Request"}, 400

    def http_method_not_allowed(self, request, *args, **kwargs):
        super().http_method_not_allowed(request, *args, **kwargs)
        return {"error": "405 Method Not Allowed"}, 405

    @method_decorator(require_ajax)
    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed

        response = handler(request, *args, **kwargs)

        if isinstance(response, tuple):
            # Status code included
            return self.render_to_json_response(*response)

        return self.render_to_json_response(response)


class JsonView(View):
    """**DEPRECATED** will use JSONView"""
    request_data = None
    data = None
    success_message = "oldu"
    error_message = "olmadı"
    bad_request_message = "400 Bad Request"
    method = None  # required for foce_get/force_post decorators.

    def handle(self):
        if self.data is not None:
            return self.render_to_json_response()

        if settings.DEBUG:
            raise ValueError(f"The view {self.__class__.__name__} returned nothing")

        return self.error()

    def render_to_json_response(self, status=200):
        return JsonResponse(self.data, status=status)

    @method_decorator(require_ajax)
    def dispatch(self, request, *args, **kwargs):
        self.method = request.method.lower()

        if self.method in self.http_method_names:
            self.request_data = dict(parse_qsl(request.body.decode("utf-8"))) if self.method == "post" else request.GET
            return self.handle()

        return self.http_method_not_allowed(request, *args, **kwargs)

    def success(self, message_pop=False, redirect_url=False):
        if message_pop:
            notifications.success(self.request, self.success_message)

        self.data = {"success": True, "message": self.success_message}

        if redirect_url:
            self.data.update({"redirect_to": redirect_url})

        return self.render_to_json_response()

    def error(self, message_pop=False, status=500):
        if message_pop:
            notifications.error(self.request, self.error_message)

        self.data = {"success": False, "message": self.error_message}
        return self.render_to_json_response(status=status)

    def bad_request(self):
        self.data = {"success": False, "message": self.bad_request_message}
        return self.render_to_json_response(status=400)
