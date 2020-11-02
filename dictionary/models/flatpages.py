from django.contrib.flatpages.models import FlatPage
from django.db import models
from django.utils.translation import gettext_lazy as _


class MetaFlatPage(FlatPage):
    html_only = models.BooleanField(
        default=False,
        verbose_name=_("Allow HTML"),
        help_text=_("Check this to only use HTML, otherwise you can use entry formatting options."),
    )
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_("Weight"))

    class Meta:
        ordering = ("-weight", "url")
        verbose_name = _("flat page")
        verbose_name_plural = _("flat pages")


class ExternalURL(models.Model):
    name = models.CharField(max_length=64, verbose_name=_("Name"))
    url = models.URLField(verbose_name=_("Link"))
    weight = models.PositiveSmallIntegerField(default=0, verbose_name=_("Weight"))

    class Meta:
        ordering = ("-weight", "name")
        verbose_name = _("external url")
        verbose_name_plural = _("external urls")

    def __str__(self):
        return f"{self.name} -- {self.url}"
