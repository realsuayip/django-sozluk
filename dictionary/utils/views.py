from django.contrib import messages as notifications
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import View

from .decorators import require_ajax


class JsonView(UserPassesTestMixin, View):
    login_required = False
    require_method = None  # "post" or "get" applies to WHOLE view
    request_data = None
    method = None
    success_message = "oldu"
    error_message = "olmadı"
    bad_request_message = "400 Bad Request"

    def handle_no_permission(self):
        return JsonResponse({"error": "You lack permissions to view this page."}, status=403)

    def test_func(self):
        logged_in = self.request.user.is_authenticated

        if self.request.method == "POST":
            self.method = "post"
        elif self.request.method == "GET":
            self.method = "get"

        if self.require_method is not None:
            if self.method != self.require_method.lower():
                return False

        if self.login_required:
            if not logged_in:
                return False
        return True

    def handle(self):
        return self.error()

    def get_data(self, method):
        self.request_data = method
        return self.handle()

    @method_decorator(require_ajax)
    def get(self, *args, **kwargs):
        return self.get_data(self.request.GET)

    @method_decorator(require_ajax)
    def post(self, *args, **kwargs):
        return self.get_data(self.request.POST)

    def success(self, message_pop=False, redirect_url=False):
        if message_pop:
            notifications.success(self.request, self.success_message)

        if redirect_url:
            return JsonResponse({"success": True, "message": self.success_message, "redirect_to": redirect_url},
                                status=200)

        return JsonResponse({"success": True, "message": self.success_message}, status=200)

    def error(self, message_pop=False, status=500):
        if message_pop:
            notifications.success(self.request, self.error_message)
        return JsonResponse({"success": False, "message": self.error_message}, status=status)

    def bad_request(self):
        return JsonResponse({"success": False, "message": self.bad_request_message}, status=400)
