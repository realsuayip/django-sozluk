from django.core.cache import cache
from django.db import models
from django.db.models import Sum, UniqueConstraint
from django.db.models.functions import Coalesce
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _

from uuslug import uuslug

from dictionary.conf import settings
from dictionary.models.managers.category import CategoryManager, CategoryManagerAll
from dictionary.utils.validators import validate_category_name


class Category(models.Model):
    name = models.CharField(max_length=24, unique=True, verbose_name=_("Name"), validators=[validate_category_name])
    slug = models.SlugField(editable=False)
    description = models.TextField(blank=True, verbose_name=_("Description"))
    is_pseudo = models.BooleanField(
        default=False,
        verbose_name=_("Pseudo channel"),
        help_text=_(
            "Pseudo channels cannot be browsed by the users but can be assigned"
            " to the topics. You can add these channels to popular exclusions."
        ),
    )
    is_default = models.BooleanField(
        default=True,
        verbose_name=_("Default"),
        help_text=_(
            "When checked, this channel will be present in the following"
            " channels of newly registered users. (Pseudo channels are excluded.)"
        ),
    )
    weight = models.SmallIntegerField(default=0, verbose_name=_("Weight"))

    objects_all = CategoryManagerAll()
    objects = CategoryManager()

    class Meta:
        ordering = ["-weight"]
        verbose_name = _("channel")
        verbose_name_plural = _("channels")

    def __str__(self):
        return f"{self.name}"

    def save(self, *args, **kwargs):
        self.slug = uuslug(self.name, instance=self)

        # Deletes cache of context processor that holds list of categories.
        cache.delete("default_context__header_categories")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("topic_list", kwargs={"slug": self.slug})


class Suggestion(models.Model):
    class Direction(models.IntegerChoices):
        POSITIVE = 1, _("Positive")
        NEGATIVE = -1, _("Negative")

    author = models.ForeignKey("Author", on_delete=models.CASCADE, verbose_name=_("Author"))
    topic = models.ForeignKey(
        "Topic", on_delete=models.CASCADE, related_name="category_suggestions", verbose_name=_("Topic")
    )
    category = models.ForeignKey("Category", on_delete=models.CASCADE, related_name="+", verbose_name=_("Channel"))

    direction = models.SmallIntegerField(choices=Direction.choices, verbose_name=_("Direction"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))

    class Meta:
        verbose_name = _("suggestion")
        verbose_name_plural = _("suggestions")
        constraints = [
            UniqueConstraint(fields=["author", "topic", "category"], name="unique_category_suggestion"),
        ]

    def __str__(self):
        return f"{self._meta.verbose_name.title()} #{self.pk}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.register()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.register()

    def register(self):
        rate = self.__class__.objects.filter(topic=self.topic, category=self.category).aggregate(
            rate=Coalesce(Sum("direction"), 0)
        )["rate"]

        exists = self.topic.category.filter(pk=self.category_id).exists()

        if not exists and rate >= settings.SUGGESTIONS_QUALIFY_RATE:
            self.topic.category.add(self.category)

        if exists and rate < settings.SUGGESTIONS_QUALIFY_RATE:
            self.topic.category.remove(self.category)
