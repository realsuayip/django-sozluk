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
            return self._response()

        if settings.DEBUG:
            raise ValueError(f"The view {self.__class__.__name__} returned nothing")
        return self.error()

    def _response(self, status=200):
        return JsonResponse(self.data, status=status)

    def _get_data(self, request_data):
        self.request_data = request_data
        return self.handle()

    @method_decorator(require_ajax)
    def get(self, *args, **kwargs):
        self.method = "get"
        return self._get_data(self.request.GET)

    @method_decorator(require_ajax)
    def post(self, *args, **kwargs):
        self.method = "post"
        return self._get_data(self.request.POST)

    def success(self, message_pop=False, redirect_url=False):
        if message_pop:
            notifications.success(self.request, self.success_message)

        self.data = dict(success=True, message=self.success_message)

        if redirect_url:
            self.data.update({"redirect_to": redirect_url})

        return self._response()

    def error(self, message_pop=False, status=500):
        if message_pop:
            notifications.error(self.request, self.error_message)

        self.data = dict(success=False, message=self.error_message)
        return self._response(status=status)

    def bad_request(self):
        self.data = dict(success=False, message=self.bad_request_message)
        return self._response(status=400)
