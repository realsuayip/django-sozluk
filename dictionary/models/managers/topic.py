from django.db import models
from django.db.models import Count, Q
from django.http import Http404

from ...models import Entry
from ...utils import turkish_lower


class TopicManager(models.Manager):
    class PseudoTopic:
        def __init__(self, title):
            self.title = turkish_lower(title).strip()
            self.exists = False

        def __str__(self):
            return f"<{self.__class__.__name__} {self.title}>"

    def get_or_pseudo(self, slug=None, unicode_string=None, entry_id=None):

        if slug:
            try:
                return self.get(slug=slug)
            except self.model.DoesNotExist:
                return self.PseudoTopic(slug)

        elif unicode_string:
            try:
                return self.get(title=unicode_string)
            except self.model.DoesNotExist:
                return self.PseudoTopic(unicode_string)

        elif entry_id:
            try:
                return Entry.objects_published.get(id=entry_id).topic
            except Entry.DoesNotExist:
                raise Http404
        else:
            raise ValueError("No arguments given.")

    def create_topic(self, title, created_by=None):
        topic = self.create(title=title, created_by=created_by)
        return topic


class TopicManagerPublished(models.Manager):
    # Return topics which has published (by authors) entries
    def get_queryset(self):
        pub_filter = {"entries__is_draft": False, "entries__author__is_novice": False}
        return super().get_queryset().annotate(num_published=Count("entries", filter=Q(**pub_filter))).exclude(
            num_published__lt=1)
