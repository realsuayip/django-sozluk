from django.db import models
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _lazy

from uuslug import uuslug

from ..templatetags.filters import entrydate


class Announcement(models.Model):
    title = models.CharField(max_length=254, verbose_name=_lazy("Title"))
    content = models.TextField(verbose_name=_lazy("Content"))
    slug = models.SlugField(editable=False)

    discussion = models.ForeignKey(
        "Topic",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_lazy("Discussion topic"),
        help_text=_lazy("Optional. The topic where the users will be discussing this announcement."),
    )

    html_only = models.BooleanField(
        default=False,
        verbose_name=_lazy("Allow HTML"),
        help_text=_lazy("Check this to only use HTML, otherwise you can use entry formatting options."),
    )

    notify = models.BooleanField(
        default=False,
        verbose_name=_lazy("Notify users"),
        help_text=_lazy("When checked, users will get a notification when the announcement gets released."),
    )

    date_edited = models.DateTimeField(null=True, editable=False)
    date_created = models.DateTimeField(
        verbose_name=_lazy("Publication date"), help_text=_lazy("You can set future dates for the publication date."),
    )

    def __str__(self):
        return f"{self.title} - {entrydate(timezone.localtime(self.date_created), None)}"

    def save(self, *args, **kwargs):
        created = self.pk is None

        if created:
            self.slug = uuslug(self.title, instance=self)
        elif self.date_created < timezone.now():
            # Pre-save content check for published announcement
            previous = Announcement.objects.get(pk=self.pk)

            if previous.content != self.content or previous.title != self.title:
                self.date_edited = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        pub = timezone.localtime(self.date_created)
        return reverse(
            "announcements-detail", kwargs={"year": pub.year, "month": pub.month, "day": pub.day, "slug": self.slug},
        )

    class Meta:
        verbose_name = _lazy("announcement")
        verbose_name_plural = _lazy("announcements")
