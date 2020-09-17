from functools import wraps

from django.db.models import F
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from dictionary.conf import settings
from dictionary.models.author import Author
from dictionary.models.entry import Entry
from dictionary.models.topic import Topic


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

    rate = settings.VOTE_RATES["favorite"]

    if action == "post_add":
        entries.update(vote_rate=F("vote_rate") + rate)
    else:
        entries.update(vote_rate=F("vote_rate") - rate)


@receiver(m2m_changed, sender=Author.upvoted_entries.through)
@entrym2m
def update_vote_rate_upvote(action, entries, **kwargs):
    """Signal to update vote rate of an entry after the user upvotes it."""

    rate = settings.VOTE_RATES["vote"]

    if action == "post_add":
        entries.update(vote_rate=F("vote_rate") + rate)
    else:
        entries.update(vote_rate=F("vote_rate") - rate)


@receiver(m2m_changed, sender=Author.downvoted_entries.through)
@entrym2m
def update_vote_rate_downvote(action, entries, **kwargs):
    """Signal to update vote rate of an entry after the user downvotes it."""

    rate = settings.VOTE_RATES["vote"]

    if action == "post_add":
        entries.update(vote_rate=F("vote_rate") - rate)
    else:
        entries.update(vote_rate=F("vote_rate") + rate)


@receiver(m2m_changed, sender=Topic.mirrors.through)
def update_topic_disambiguation(instance, action, pk_set, **kwargs):
    """Signal to auto update all mirrors of given topic's related objects."""

    appended_topics = Topic.objects.filter(pk__in=pk_set)
    current = instance.mirrors.all()

    if action not in ("post_add", "post_remove"):
        return

    for topic in appended_topics:

        related = topic.mirrors.all()

        for mirror in related:
            if mirror != instance:
                if action == "post_add":
                    if mirror not in current:
                        instance.mirrors.add(mirror)
                else:
                    if mirror in current:
                        instance.mirrors.remove(mirror)

        for neighbor in current:
            if neighbor != topic:
                if neighbor not in related:
                    if action == "post_add":
                        topic.mirrors.add(neighbor)
                else:
                    if action == "post_remove":
                        topic.mirrors.remove(neighbor)
