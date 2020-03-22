from django.db.models import F
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from ..models.author import Author, Entry
from ..utils.settings import VOTE_RATES


@receiver(m2m_changed, sender=Author.favorite_entries.through)
def update_vote_rate_favorite(action, pk_set, **kwargs):
    """Signal to update vote rate of an entry after the user favorites it."""

    if action in ("post_add", "post_remove"):
        entries = Entry.objects_published.filter(pk__in=pk_set)
        rate = VOTE_RATES["favorite"]

        if action == "post_add":
            entries.update(vote_rate=F("vote_rate") + rate)
        else:
            entries.update(vote_rate=F("vote_rate") - rate)
