from django.http import Http404
from django.db import models

from ...models import Entry


class TopicManager(models.Manager):

    class PseudoTopic:
        def __init__(self, title):
            self.title = title
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
