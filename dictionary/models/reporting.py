from django.db import models


class GeneralReport(models.Model):
    CONTENT = 'CNT'
    OTHER = 'ETC'
    CATEGORIES = ((CONTENT, 'sözlükte yayınlanan içerikler hakkında'), (OTHER, 'sözlükle ilgili diğer konlar'))

    reporter_email = models.EmailField(verbose_name=" e-posta adresi")
    category = models.CharField(max_length=3, choices=CATEGORIES, verbose_name=" kategori")
    subject = models.CharField(max_length=160, verbose_name=" konu")
    content = models.TextField(verbose_name=" düşünceleriniz")
    is_open = models.BooleanField(default=True, verbose_name="bu raporun statüsü açık")

    def __str__(self):
        return f"{self.subject} <{self.__class__.__name__}>#{self.pk}"
