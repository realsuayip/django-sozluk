from contextlib import suppress

from django.core.validators import ValidationError
from django.db import models
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404

from dictionary.models import Entry
from dictionary.utils import i18n_lower


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
        pseudo = self.PseudoTopic(title)

        try:
            self.model(title=title).full_clean()
        except ValidationError:
            return pseudo

        pseudo.valid = True
        return pseudo

    @staticmethod
    def _format_title(title):
        return i18n_lower(title).strip()

    def get_or_pseudo(self, slug=None, unicode_string=None, entry_id=None):
        if unicode_string is not None:
            unicode_string = self._format_title(unicode_string)
            with suppress(self.model.DoesNotExist):
                return self.get(title=unicode_string)
            return self._get_pseudo(unicode_string)

        if slug is not None:
            slug = self._format_title(slug)
            with suppress(self.model.DoesNotExist):
                return self.get(slug=slug)
            return self._get_pseudo(slug)

        if entry_id is not None:
            entry = get_object_or_404(Entry.objects_published, pk=entry_id)
            return entry.topic

        raise ValueError("No arguments given.")

    def create_topic(self, title, created_by=None):
        topic = self.create(title=title, created_by=created_by)
        return topic


class TopicManagerPublished(models.Manager):
    # Return topics which has published (by authors) entries
    def get_queryset(self):
        return super().get_queryset().filter(Exists(Entry.objects.filter(topic=OuterRef("pk"))))
