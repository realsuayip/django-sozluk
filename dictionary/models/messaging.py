from django.db import models
from django.utils import timezone

from .author import Author
from .managers.messaging import ConversationManager, MessageManager


class Message(models.Model):
    body = models.TextField()
    sender = models.ForeignKey(Author, related_name="+", on_delete=models.PROTECT)
    recipient = models.ForeignKey(Author, related_name="+", on_delete=models.PROTECT)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    objects = MessageManager()

    class Meta:
        ordering = ["sent_at"]

    def mark_read(self):
        self.read_at = timezone.now()
        self.save()

    def __str__(self):
        return str(self.pk)


class Conversation(models.Model):
    participants = models.ManyToManyField(Author)
    messages = models.ManyToManyField(Message)

    objects = ConversationManager()

    def __str__(self):
        return f"{self.id}{self.participants.values_list('username', flat=True)}"

    @property
    def last_message(self):
        return self.messages.latest(field_name="sent_at")
