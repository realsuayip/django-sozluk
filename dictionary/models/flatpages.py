from django.contrib.flatpages.models import FlatPage
from django.db import models
from django.utils.translation import gettext_lazy as _lazy


class MetaFlatPage(FlatPage):
    html_only = models.BooleanField(
        default=False,
        verbose_name=_lazy("Allow HTML"),
        help_text=_lazy("Check this to only use HTML, otherwise you can use entry formatting options."),
    )
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_lazy("Weight"))

    class Meta:
        ordering = ("-weight", "url")
        verbose_name = _lazy("flat page")
        verbose_name_plural = _lazy("flat pages")


class ExternalURL(models.Model):
    name = models.CharField(max_length=64, verbose_name=_lazy("Name"))
    url = models.URLField(verbose_name=_lazy("Link"))
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_lazy("Weight"))

    def __str__(self):
        return f"{self.name} -- {self.url}"

    class Meta:
        ordering = ("-weight", "name")
        verbose_name = _lazy("external url")
        verbose_name_plural = _lazy("external urls")
