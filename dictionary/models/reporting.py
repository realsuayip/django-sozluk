from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _


class GeneralReport(models.Model):
    class CategoryPref(models.TextChoices):
        CONTENT = "CNT", _("about the some content published")
        OTHER = "ETC", _("about other subjects")

    reporter_email = models.EmailField(verbose_name=_("e-mail"))
    category = models.CharField(
        max_length=3,
        choices=CategoryPref.choices,
        verbose_name=_("category"),
        default=CategoryPref.CONTENT,
    )
    subject = models.CharField(max_length=160, verbose_name=_("Subject"))
    content = models.TextField(verbose_name=_("Content"))
    is_open = models.BooleanField(
        default=True,
        verbose_name=_("Report is open"),
        help_text=_("Indicates the current status of the report."),
    )

    key = models.UUIDField(default=uuid4, unique=True, editable=False)
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Verified"),
        help_text=_("Indicates whether this report has been verified by e-mail"),
    )

    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_verified = models.DateTimeField(null=True, verbose_name=_("Date verified"))

    class Meta:
        verbose_name = _("report")
        verbose_name_plural = _("reports")

    def __str__(self):
        return f"{self.subject} <{self.__class__.__name__}>#{self.pk}"
