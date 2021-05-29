from decimal import Decimal

from django.db import models
from django.db.models import F
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from dictionary.models.managers.entry import EntryManager, EntryManagerAll, EntryManagerOnlyPublished
from dictionary.models.messaging import Message
from dictionary.utils import get_generic_privateuser, get_generic_superuser, smart_lower
from dictionary.utils.validators import validate_user_text


class Entry(models.Model):
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="entries", verbose_name=_("Topic"))
    author = models.ForeignKey("Author", on_delete=models.CASCADE, verbose_name=_("Author"))
    content = models.TextField(validators=[validate_user_text], verbose_name=_("Content"))
    date_created = models.DateTimeField(db_index=True, auto_now_add=True, verbose_name=_("Date created"))
    date_edited = models.DateTimeField(blank=True, null=True, default=None, verbose_name=_("Date edited"))
    vote_rate = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal(0), verbose_name=_("Vote rate"))
    is_draft = models.BooleanField(db_index=True, default=False, verbose_name=_("Draft status"))

    objects_all = EntryManagerAll()
    objects_published = EntryManagerOnlyPublished()
    objects = EntryManager()

    class Meta:
        # TODO: add GinIndex with gin_trgm_ops when dropping support for other databases.
        ordering = ["date_created"]
        verbose_name = _("entry")
        verbose_name_plural = _("entries")

    def __str__(self):
        return f"{self.id}#{self.author}"

    def save(self, *args, **kwargs):
        created = self.pk is None
        self.content = smart_lower(self.content)

        if created:
            self.author.invalidate_entry_counts()

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

    def delete(self, *args, **kwargs):
        if self.comments.exists():
            self.author = get_generic_privateuser()
            self.save()
            return

        self.author.invalidate_entry_counts()
        super().delete(*args, **kwargs)

        if self.author.is_novice and self.author.application_status == "PN" and self.author.entry_count < 10:
            # If the entry count drops less than 10, remove user from novice lookup.
            # This does not trigger if bulk deletion made on admin panel (users can
            # only remove one entry at a time) or the entry in question has answers.
            self.author.application_status = "OH"
            self.author.application_date = None
            self.author.queue_priority = 0
            self.author.save(update_fields=["application_status", "application_date", "queue_priority"])

    def get_absolute_url(self):
        return reverse("entry-permalink", kwargs={"entry_id": self.pk})

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

    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_edited = models.DateTimeField(null=True, editable=False, verbose_name=_("Date edited"))

    class Meta:
        verbose_name = _("comment")
        verbose_name_plural = _("comments")

    def __str__(self):
        return gettext("Comment #%(number)d") % {"number": self.pk}

    def save(self, *args, **kwargs):
        self.content = smart_lower(self.content)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('entry-permalink', kwargs={'entry_id': self.entry_id})}#comment-{self.pk}"
