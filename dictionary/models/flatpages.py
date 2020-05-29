from django.contrib.flatpages.models import FlatPage
from django.db import models


class MetaFlatPage(FlatPage):
    html_only = models.BooleanField(
        default=False,
        verbose_name="HTML açık",
        help_text="Sadece HTML kullanmak için bunu seçin,"
        " aksi halde entry biçimlendirme seçenekleri kullanılabilir.",
    )
    weight = models.PositiveSmallIntegerField(default=0, verbose_name="Sıra")

    class Meta:
        ordering = ("-weight", "url")
        verbose_name = "düz sayfa"
        verbose_name_plural = "düz sayfalar"


class ExternalURL(models.Model):
    name = models.CharField(max_length=64, verbose_name="İsim")
    url = models.URLField(verbose_name="Bağlantı")
    weight = models.PositiveSmallIntegerField(default=0, verbose_name="Sıra")

    def __str__(self):
        return f"{self.name} -- {self.url}"

    class Meta:
        ordering = ("-weight", "name")
        verbose_name = "dış bağlantı"
        verbose_name_plural = "dış bağlantılar"
