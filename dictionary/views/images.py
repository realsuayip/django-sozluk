from io import BytesIO

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.files import File
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils.translation import gettext
from django.views.generic import CreateView, ListView, View
from django.views.generic.detail import SingleObjectMixin

from PIL import Image as PIL_Image, ImageOps

from dictionary.conf import settings
from dictionary.models import Image
from dictionary.utils import time_threshold


def compress(file):
    img, img_io = PIL_Image.open(file), BytesIO()
    transposed = ImageOps.exif_transpose(img)
    transposed.save(img_io, img.format, quality=settings.COMPRESS_QUALITY)
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
        ).count() >= settings.DAILY_IMAGE_UPLOAD_LIMIT and not self.request.user.has_perm("dictionary.add_image"):
            return HttpResponseBadRequest(
                gettext("you have reached the upload limit (%(limit)d images in a 24 hour period). try again later.")
                % {"limit": settings.DAILY_IMAGE_UPLOAD_LIMIT}
            )

        if image.file.size > settings.MAX_UPLOAD_SIZE:
            return HttpResponseBadRequest(
                gettext("this file is too large. (%.1f> MB)") % settings.MAX_UPLOAD_SIZE / 1048576
            )

        if settings.COMPRESS_IMAGES and image.file.size > settings.COMPRESS_THRESHOLD:
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
        # Notice: AnonymousUser has "has_perm" property.
        if self.request.user.has_perm("dictionary.view_image"):
            return super().get_queryset()

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
        response = HttpResponse(content_type="image/png")
        response[settings.XSENDFILE_HEADER_NAME] = image.file.url
        return response
