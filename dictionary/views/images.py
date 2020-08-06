from io import BytesIO

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files import File
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext
from django.views.generic import CreateView, ListView, View
from django.views.generic.detail import SingleObjectMixin

from PIL import Image as PIL_Image

from ..models import Image
from ..utils import time_threshold
from ..utils.settings import (
    COMPRESS_IMAGES,
    COMPRESS_QUALITY,
    COMPRESS_THRESHOLD,
    DAILY_IMAGE_UPLOAD_LIMIT,
    MAX_UPLOAD_SIZE,
    XSENDFILE_HEADER_NAME,
)


def compress(file):
    img, img_io = PIL_Image.open(file), BytesIO()
    img.save(img_io, img.format, quality=COMPRESS_QUALITY)
    return File(img_io, name=file.name)


class ImageUpload(LoginRequiredMixin, CreateView):
    http_method_names = ["post"]
    model = Image
    fields = ("file",)

    def form_valid(self, form):
        image = form.save(commit=False)

        if self.request.user.is_novice or not self.request.user.is_accessible:
            return HttpResponseBadRequest(gettext("you lack the required permissions."))

        if Image.objects.filter(
            author=self.request.user, date_created__gte=time_threshold(hours=24)
        ).count() >= DAILY_IMAGE_UPLOAD_LIMIT and not self.request.user.has_perm("dictionary.add_image"):
            return HttpResponseBadRequest(
                gettext("you have reached the upload limit (%(limit)d images in a 24 hour period). try again later.")
                % {"limit": DAILY_IMAGE_UPLOAD_LIMIT}
            )

        if image.file.size > MAX_UPLOAD_SIZE:
            return HttpResponseBadRequest(gettext("this file is too large. (%.1f> MB)") % MAX_UPLOAD_SIZE / 1048576)

        if COMPRESS_IMAGES and image.file.size > COMPRESS_THRESHOLD:
            image.file = compress(image.file)

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


class ImageDetailDevelopment(ImageDetailBase):
    def get(self, request, *args, **kwargs):
        image = self.get_object()

        try:
            return HttpResponse(image.file, content_type="image/png")
        except FileNotFoundError:
            return HttpResponse("File not found.")


class ImageDetailProduction(ImageDetailBase):
    """
    Notice: The default settings only support Nginx. Set XSENDFILE_HEADER_NAME
    according to your server. You may need some extra set-up.
    """

    def get(self, request, *args, **kwargs):
        image = self.get_object()
        response = HttpResponse(content_type="image_png")
        response[XSENDFILE_HEADER_NAME] = image.file.url
        return response
