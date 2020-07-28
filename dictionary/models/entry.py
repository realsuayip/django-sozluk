from decimal import Decimal

from django.db import models
from django.db.models import F
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from ..models.messaging import Message
from ..utils import get_generic_superuser, i18n_lower
from ..utils.validators import validate_user_text
from .managers.entry import EntryManager, EntryManagerAll, EntryManagerOnlyPublished


class Entry(models.Model):
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="entries")
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    content = models.TextField(validators=[validate_user_text])
    date_created = models.DateTimeField(auto_now_add=True)
    date_edited = models.DateTimeField(blank=True, null=True, default=None)
    vote_rate = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal(0))
    is_draft = models.BooleanField(default=False)

    objects_all = EntryManagerAll()
    objects_published = EntryManagerOnlyPublished()
    objects = EntryManager()

    def __str__(self):
        return f"{self.id}#{self.author}"

    class Meta:
        ordering = ["date_created"]
        verbose_name_plural = "entry"

    def save(self, *args, **kwargs):
        self.content = i18n_lower(self.content)
        super().save(*args, **kwargs)

        # Check if the user has written 10 entries, If so make them available for novice lookup
        if self.author.is_novice and self.author.application_status == "OH" and self.author.entry_count >= 10:
            self.author.application_status = "PN"
            self.author.application_date = timezone.now()
            self.author.save()

            Message.objects.compose(
                get_generic_superuser(),
                self.author,
                gettext(
                    "as you entered your first 10 entries, you have been admitted to"
                    " the novice list. you can see your queue number in your profile page."
                    " if your entry count drops below 10, you will be kicked from the list."
                ),
            )

        # assign topic creator (includes novices)
        if not self.is_draft and not self.topic.created_by:
            self.topic.created_by = self.author
            self.topic.save()

        self.topic.register_wishes(fulfiller_entry=self)

    def get_absolute_url(self):
        return reverse("entry-permalink", kwargs={"entry_id": self.pk})

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.author.is_novice and self.author.application_status == "PN" and self.author.entry_count < 10:
            # if the entry count drops less than 10, remove user from novice lookup
            # does not work if bulk deletion made on admin panel (users can only remove one entry at a time)
            self.author.application_status = "OH"
            self.author.application_date = None
            self.author.queue_priority = 0
            self.author.save()

    def update_vote(self, rate, change=False):
        k = Decimal("2") if change else Decimal("1")
        self.vote_rate = F("vote_rate") + rate * k
        self.save()


class Comment(models.Model):
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey("Author", on_delete=models.CASCADE, related_name="+", verbose_name=_("Author"))
    content = models.TextField(validators=[validate_user_text], verbose_name=_("Content"))

    upvoted_by = models.ManyToManyField("Author", related_name="+")
    downvoted_by = models.ManyToManyField("Author", related_name="+")

    date_created = models.DateTimeField(auto_now_add=True)
    date_edited = models.DateTimeField(null=True, editable=False)

    class Meta:
        verbose_name = _("comment")
        verbose_name_plural = _("comments")

    def __str__(self):
        return gettext("Comment #%(number)d") % {"number": self.pk}

    def save(self, *args, **kwargs):
        self.content = i18n_lower(self.content)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('entry-permalink', kwargs={'entry_id': self.entry.pk})}#comment-{self.pk}"
