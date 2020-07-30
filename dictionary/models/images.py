import secrets
import string
import uuid

from django.db import models


def user_directory_path(_instance, filename):
    ext = filename.split(".")[-1]
    return f"{uuid.uuid4().hex}.{ext}"


def image_slug():
    """Assigns a slug to an image. (Tries again recursively if the slug is taken.)"""
    slug = "".join(secrets.choice(string.ascii_letters + string.digits) for _i in range(8))

    try:
        Image.objects.get(slug=slug)
        return image_slug()
    except Image.DoesNotExist:
        return slug


class Image(models.Model):
    author = models.ForeignKey("Author", null=True, on_delete=models.SET_NULL)
    file = models.ImageField(upload_to=user_directory_path)
    slug = models.SlugField(default=image_slug, unique=True, editable=False)
    is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self):
        return self.file.url

    def delete(self, *args, **kwargs):
        super().delete()
        self.file.delete(save=False)

    def __str__(self):
        return str(self.slug)
