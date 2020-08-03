from django.db import models
from django.db.models import Sum, UniqueConstraint
from django.db.models.functions import Coalesce
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _

from uuslug import uuslug

from ..utils.settings import SUGGESTIONS_QUALIFY_RATE
from ..utils.validators import validate_category_name


class Category(models.Model):
    name = models.CharField(max_length=24, unique=True, verbose_name=_("Name"), validators=[validate_category_name])
    slug = models.SlugField(editable=False)
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    weight = models.SmallIntegerField(default=0, verbose_name=_("Weight"))

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        self.slug = uuslug(self.name, instance=self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("topic_list", kwargs={"slug": self.slug})

    class Meta:
        ordering = ["-weight"]
        verbose_name = _("channel")
        verbose_name_plural = _("channels")


class Suggestion(models.Model):
    POSITIVE = 1
    NEGATIVE = -1
    DIRECTIONS = ((POSITIVE, _("Positive")), (NEGATIVE, _("Negative")))

    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="category_suggestions")
    category = models.ForeignKey("Category", on_delete=models.CASCADE, related_name="+")

    direction = models.SmallIntegerField(choices=DIRECTIONS)
    date_created = models.DateTimeField(auto_now_add=True)

    def register(self):
        rate = self.__class__.objects.filter(topic=self.topic, category=self.category).aggregate(
            rate=Coalesce(Sum("direction"), 0)
        )["rate"]

        exists = self.topic.category.filter(pk=self.category.pk).exists()

        if not exists and rate >= SUGGESTIONS_QUALIFY_RATE:
            self.topic.category.add(self.category)

        if exists and rate < SUGGESTIONS_QUALIFY_RATE:
            self.topic.category.remove(self.category)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.register()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.register()

    class Meta:
        constraints = [
            UniqueConstraint(fields=["author", "topic", "category"], name="unique_category_suggestion"),
        ]
