from django.db import models

from uuslug import uuslug


class Category(models.Model):
    name = models.CharField(max_length=24, unique=True)
    slug = models.SlugField(max_length=64, unique=False, blank=True)
    description = models.TextField(null=True, blank=True)
    weight = models.SmallIntegerField(default=0)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["-weight"]

    def save(self, *args, **kwargs):
        self.slug = uuslug(self.name, instance=self)
        super().save(*args, **kwargs)
