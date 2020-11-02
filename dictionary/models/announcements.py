from django.db import models
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from uuslug import uuslug

from dictionary.templatetags.filters import entrydate


class Announcement(models.Model):
    title = models.CharField(max_length=254, verbose_name=_("Title"))
    content = models.TextField(verbose_name=_("Content"))
    slug = models.SlugField(editable=False)

    discussion = models.ForeignKey(
        "Topic",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Discussion topic"),
        help_text=_("Optional. The topic where the users will be discussing this announcement."),
    )

    html_only = models.BooleanField(
        default=False,
        verbose_name=_("Allow HTML"),
        help_text=_("Check this to only use HTML, otherwise you can use entry formatting options."),
    )

    notify = models.BooleanField(
        default=False,
        verbose_name=_("Notify users"),
        help_text=_("When checked, users will get a notification when the announcement gets released."),
    )

    date_edited = models.DateTimeField(null=True, editable=False)
    date_created = models.DateTimeField(
        db_index=True,
        verbose_name=_("Publication date"),
        help_text=_("You can set future dates for the publication date."),
    )

    class Meta:
        verbose_name = _("announcement")
        verbose_name_plural = _("announcements")

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
            "announcements-detail",
            kwargs={"year": pub.year, "month": pub.month, "day": pub.day, "slug": self.slug},
        )
