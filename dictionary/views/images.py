from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext
from django.views.generic import CreateView, ListView, View
from django.views.generic.detail import SingleObjectMixin

from ..models import Image


MAX_UPLOAD_SIZE = 2621440  # 2.5MB


class ImageUpload(LoginRequiredMixin, CreateView):
    http_method_names = ["post"]
    model = Image
    fields = ("file",)

    def form_valid(self, form):
        image = form.save(commit=False)

        if self.request.user.is_novice or not self.request.user.is_accessible:
            return HttpResponseBadRequest(gettext("You lack the required permissions."))

        if image.file.size > MAX_UPLOAD_SIZE:
            return HttpResponseBadRequest("This file is too large. (>2.5 MB)")

        image.author = self.request.user
        image.save()
        return JsonResponse({"slug": image.slug})

    def form_invalid(self, form):
        return HttpResponseBadRequest(form.errors["file"])


class ImageList(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "dictionary/list/image_list.html"

    def get_queryset(self):
        return Image.objects.filter(author=self.request.user, is_deleted=False).order_by("-date_created")

    def test_func(self):
        return not self.request.user.is_novice


class ImageDetailBase(SingleObjectMixin, View):
    model = Image

    def get_queryset(self):
        return self.model.objects.filter(is_deleted=False)

    def handle_exception(self):
        return HttpResponse("An error occured.")


class ImageDetailDevelopment(ImageDetailBase):
    def get(self, request, *args, **kwargs):
        image = self.get_object()

        try:
            return HttpResponse(image.file, content_type="image/png")
        except FileNotFoundError:
            return self.handle_exception()


class ImageDetailNginx(ImageDetailBase):
    def get(self, request, *args, **kwargs):
        image = self.get_object()
        response = HttpResponse(content_type="image_png")
        response["X-Accel-Redirect"] = image.file.url
        return response
