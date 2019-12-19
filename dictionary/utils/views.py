from django.conf import settings
from django.contrib import messages as notifications
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import View

from .decorators import require_ajax


class JsonView(View):
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
            self.request_data = getattr(request, request.method)
            return self.handle()

        return self.http_method_not_allowed(request, *args, **kwargs)

    def success(self, message_pop=False, redirect_url=False):
        if message_pop:
            notifications.success(self.request, self.success_message)

        self.data = dict(success=True, message=self.success_message)

        if redirect_url:
            self.data.update({"redirect_to": redirect_url})

        return self.render_to_json_response()

    def error(self, message_pop=False, status=500):
        if message_pop:
            notifications.error(self.request, self.error_message)

        self.data = dict(success=False, message=self.error_message)
        return self.render_to_json_response(status=status)

    def bad_request(self):
        self.data = dict(success=False, message=self.bad_request_message)
        return self.render_to_json_response(status=400)
