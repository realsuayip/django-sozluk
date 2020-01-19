from django.db import models
from django.shortcuts import reverse
from uuslug import uuslug


class Category(models.Model):
    name = models.CharField(max_length=24, unique=True, verbose_name="isim")
    slug = models.SlugField(max_length=64, unique=False, blank=True)
    description = models.TextField(null=True, blank=True, verbose_name="açıklama")
    weight = models.SmallIntegerField(default=0, verbose_name="sıra")

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        self.slug = uuslug(self.name, instance=self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("topic_list", kwargs={"slug": self.slug})

    class Meta:
        ordering = ["-weight"]
        verbose_name = "kanal"
        verbose_name_plural = "kanallar"
