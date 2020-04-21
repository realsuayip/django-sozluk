from uuid import uuid4

from django.db import models


class GeneralReport(models.Model):
    CONTENT = "CNT"
    OTHER = "ETC"
    CATEGORIES = (
        (CONTENT, "sözlükte yayınlanan içerikler hakkında"),
        (OTHER, "sözlükle ilgili diğer konular hakkında"),
    )

    reporter_email = models.EmailField(verbose_name="E-posta adresi")
    category = models.CharField(max_length=3, choices=CATEGORIES, verbose_name="Kategori")
    subject = models.CharField(max_length=160, verbose_name="Konu")
    content = models.TextField(verbose_name="İçerik")
    is_open = models.BooleanField(
        default=True, verbose_name="Raporun statüsü açık", help_text="Bu raporun değerlendirilme durumunu belirtir."
    )

    key = models.UUIDField(default=uuid4, unique=True, editable=False)
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Onaylanmış",
        help_text="Bu raporun e-posta aracılığıyla onaylanıp onaylanmadığını belirtir.",
    )

    date_created = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma tarihi")
    date_verified = models.DateTimeField(null=True, verbose_name="Onaylanma tarihi")

    def __str__(self):
        return f"{self.subject} <{self.__class__.__name__}>#{self.pk}"

    class Meta:
        verbose_name = "rapor"
        verbose_name_plural = "raporlar"
