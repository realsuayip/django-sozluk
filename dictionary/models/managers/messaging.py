from contextlib import suppress

from django.db import models
from django.db.models import Count, Max, Q


class MessageManager(models.Manager):
    def compose(self, sender, recipient, body):
        if not sender.can_send_message(recipient):
            return False

        has_receipt = sender.allow_receipts and recipient.allow_receipts
        message = self.create(sender=sender, recipient=recipient, body=body, has_receipt=has_receipt)
        return message


class ConversationManager(models.Manager):
    def list_for_user(self, user, search_term=None):
        # List conversation list for user, provide search_term to search in messages

        if search_term:
            base = self.filter(
                Q(holder=user)
                & (Q(messages__body__icontains=search_term) | Q(messages__recipient__username__icontains=search_term)),
            )
        else:
            base = self.filter(holder=user)

        return base.annotate(
            message_sent_last=Max("messages__sent_at"),
            unread_count=Count("messages", filter=Q(messages__recipient=user, messages__read_at__isnull=True)),
        ).order_by("-message_sent_last")

    def with_user(self, sender, recipient):
        with suppress(self.model.DoesNotExist):
            return sender.conversations.get(target=recipient)

        return None
