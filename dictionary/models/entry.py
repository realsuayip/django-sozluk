from decimal import Decimal

from django.db import models
from django.db.models import F
from django.utils import timezone

from .managers.entry import EntryManager, EntryManagerAll, EntryManagerOnlyPublished


class Entry(models.Model):
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="entries")
    author = models.ForeignKey("Author", on_delete=models.PROTECT)
    content = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    date_edited = models.DateTimeField(blank=True, null=True, default=None)
    vote_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal(0))
    is_draft = models.BooleanField(default=False)

    # notice: all these managers are created after the usages, so there may be some leftovers which need to be corrected
    objects_all = EntryManagerAll()
    objects_published = EntryManagerOnlyPublished()
    objects = EntryManager()

    class Meta:
        ordering = ["date_created"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.author.is_novice and self.author.application_status == "OH":
            # Check if the user has written 10 entries, If so make them available for novice lookup
            if self.author.entry_count >= 10:
                self.author.application_status = "PN"
                self.author.application_date = timezone.now()
                self.author.save()

        # assign topic creator (includes novices)
        if not self.is_draft and not self.topic.created_by:
            self.topic.created_by = self.author
            self.topic.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.author.is_novice and self.author.application_status == "PN":
            # if the entry count drops less than 10, remove user from novice lookup
            # does not work if bulk deletion made on admin panel (users can only remove one entry at a time)
            if self.author.entry_count < 10:
                self.author.application_status = "OH"
                self.author.application_date = None
                self.author.save()

    def __str__(self):
        return f"{self.id}#{self.author}"

    def update_vote(self, rate, change=False):
        a = Decimal("2") if change else Decimal("1")
        self.vote_rate = F("vote_rate") + rate * a
        self.save()
