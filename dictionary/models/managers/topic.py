from django.core.validators import ValidationError
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from uuslug import slugify

from ...models import Entry
from ...utils import turkish_lower


class TopicManager(models.Manager):
    class PseudoTopic:
        def __init__(self, title, valid=False):
            """
            :param title: Title of the requested topic.
            :param valid: Determines if the topic could be created
            using the requested title.
            """
            self.title = title
            self.exists = False
            self.valid = valid

        def __str__(self):
            return f"<{self.__class__.__name__} {self.title}>"

    def _get_pseudo(self, title):
        title = turkish_lower(title).strip()
        pseudo = self.PseudoTopic(title)

        if not slugify(title):
            return pseudo

        try:
            self.model(title=title).full_clean()
        except ValidationError:
            return pseudo

        pseudo.valid = True
        return pseudo

    def get_or_pseudo(self, slug=None, unicode_string=None, entry_id=None):
        if unicode_string:
            try:
                return self.get(title=unicode_string)
            except self.model.DoesNotExist:
                return self._get_pseudo(unicode_string)

        elif slug:
            try:
                return self.get(slug=slug)
            except self.model.DoesNotExist:
                return self._get_pseudo(slug)

        elif entry_id:
            entry = get_object_or_404(Entry.objects_published, pk=entry_id)
            return entry.topic
        else:
            raise ValueError("No arguments given.")

    def create_topic(self, title, created_by=None):
        topic = self.create(title=title, created_by=created_by)
        return topic


class TopicManagerPublished(models.Manager):
    # Return topics which has published (by authors) entries
    def get_queryset(self):
        pub_filter = {"entries__is_draft": False, "entries__author__is_novice": False}
        return (
            super()
            .get_queryset()
            .annotate(num_published=Count("entries", filter=Q(**pub_filter)))
            .exclude(num_published__lt=1)
        )
