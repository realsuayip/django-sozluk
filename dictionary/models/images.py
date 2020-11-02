import secrets
import string
import uuid

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def user_directory_path(instance, filename):
    ext = filename.split(".")[-1]
    return f"images/{instance.author.pk}/{uuid.uuid4().hex}.{ext}"


def image_slug():
    """
    Assigns a slug to an image. (Tries again recursively if the slug is taken.)
    """

    slug = "".join(secrets.choice(string.ascii_lowercase + string.digits) for _i in range(8))

    try:
        Image.objects.get(slug=slug)
        return image_slug()
    except Image.DoesNotExist:
        return slug


class Image(models.Model):
    author = models.ForeignKey("Author", null=True, on_delete=models.SET_NULL, verbose_name=_("Author"))
    file = models.ImageField(upload_to=user_directory_path, verbose_name=_("File"))
    slug = models.SlugField(default=image_slug, unique=True, editable=False)
    is_deleted = models.BooleanField(default=False, verbose_name=_("Unpublished"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))

    class Meta:
        verbose_name = _("image")
        verbose_name_plural = _("images")

    def __str__(self):
        return str(self.slug)

    def delete(self, *args, **kwargs):
        super().delete()
        self.file.delete(save=False)

    def get_absolute_url(self):
        return reverse("image-detail", kwargs={"slug": self.slug})
