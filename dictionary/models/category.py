from uuslug import uuslug
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=24, unique=True)
    slug = models.SlugField(max_length=64, unique=False, blank=True)
    description = models.TextField()
    weight = models.SmallIntegerField(default=0)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ["-weight"]

    def save(self, *args, **kwargs):
        self.slug = uuslug(self.name, instance=self)
        super().save(*args, **kwargs)
