from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _lazy


class GeneralReport(models.Model):
    CONTENT = "CNT"
    OTHER = "ETC"
    CATEGORIES = (
        (CONTENT, _lazy("about the some content published")),
        (OTHER, _lazy("about other subjects")),
    )

    reporter_email = models.EmailField(verbose_name=_lazy("e-mail"))
    category = models.CharField(
        max_length=3, choices=CATEGORIES, verbose_name=_lazy("category"), blank=False, default=CONTENT
    )
    subject = models.CharField(max_length=160, verbose_name=_lazy("Subject"))
    content = models.TextField(verbose_name=_lazy("Content"))
    is_open = models.BooleanField(
        default=True,
        verbose_name=_lazy("Report is open"),
        help_text=_lazy("Indicates the current status of the report."),
    )

    key = models.UUIDField(default=uuid4, unique=True, editable=False)
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_lazy("Verified"),
        help_text=_lazy("Indicates whether this report has been verified by e-mail"),
    )

    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_lazy("Date created"))
    date_verified = models.DateTimeField(null=True, verbose_name=_lazy("Date verified"))

    def __str__(self):
        return f"{self.subject} <{self.__class__.__name__}>#{self.pk}"

    class Meta:
        verbose_name = _lazy("report")
        verbose_name_plural = _lazy("reports")
