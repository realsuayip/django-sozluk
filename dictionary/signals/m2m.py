from functools import wraps

from django.db.models import F
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from ..models.author import Author, Entry
from ..utils.settings import VOTE_RATES


def entrym2m(m2msignal):
    """Sets up entry signals for entry related m2m's."""

    @wraps(m2msignal)
    def decorator(action, pk_set, **kwargs):
        if action in ("post_add", "post_remove"):
            entries = Entry.objects_published.filter(pk__in=pk_set)
            return m2msignal(action, entries, **kwargs)
        return None

    return decorator


@receiver(m2m_changed, sender=Author.favorite_entries.through)
@entrym2m
def update_vote_rate_favorite(action, entries, **kwargs):
    """Signal to update vote rate of an entry after the user favorites it."""

    rate = VOTE_RATES["favorite"]

    if action == "post_add":
        entries.update(vote_rate=F("vote_rate") + rate)
    else:
        entries.update(vote_rate=F("vote_rate") - rate)


@receiver(m2m_changed, sender=Author.upvoted_entries.through)
@entrym2m
def update_vote_rate_upvote(action, entries, **kwargs):
    """Signal to update vote rate of an entry after the user upvotes it."""

    rate = VOTE_RATES["vote"]

    if action == "post_add":
        entries.update(vote_rate=F("vote_rate") + rate)
    else:
        entries.update(vote_rate=F("vote_rate") - rate)


@receiver(m2m_changed, sender=Author.downvoted_entries.through)
@entrym2m
def update_vote_rate_downvote(action, entries, **kwargs):
    """Signal to update vote rate of an entry after the user downvotes it."""

    rate = VOTE_RATES["vote"]

    if action == "post_add":
        entries.update(vote_rate=F("vote_rate") - rate)
    else:
        entries.update(vote_rate=F("vote_rate") + rate)
