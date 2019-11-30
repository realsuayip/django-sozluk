from django.db import models
from django.db.models import Count, Max


class MessageManager(models.Manager):
    def compose(self, sender, recipient, body):
        if sender == recipient or sender in recipient.blocked.all() or recipient in sender.blocked.all():
            return False

        message = self.create(sender=sender, recipient=recipient, body=body)
        return message


class ConversationManager(models.Manager):
    def list_for_user(self, user):
        # todo yanlış query, !!
        # bu query düz mantıkla yazılmalı part.._in = user, order by messages snet at.
        return self.filter(participants__in=[user]).annotate(message_sent_last=Max('messages__sent_at')).order_by(
            "-message_sent_last")

    def with_user(self, sender, recipient):
        users = [sender, recipient]
        conversation = self.annotate(count=Count('participants')).filter(count=2)
        for user in users:
            conversation = conversation.filter(participants__pk=user.pk)
        return conversation.first()
