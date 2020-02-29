from django.db import models
from django.db.models import Count, Max, Q

from ...models import Author


class MessageManager(models.Manager):
    def compose(self, sender, recipient, body):
        # Can message be sent? | (For readibility purposes) -> pylint: disable=too-many-return-statements
        if recipient.is_frozen or recipient.is_private:
            return False
        if sender == recipient:
            return False
        if recipient.message_preference == Author.DISABLED:
            return False
        if sender in recipient.blocked.all() or recipient in sender.blocked.all():
            return False
        if sender.is_novice and recipient.message_preference == Author.AUTHOR_ONLY:
            return False
        if sender not in recipient.following.all() and recipient.message_preference == Author.FOLLOWING_ONLY:
            return False

        message = self.create(sender=sender, recipient=recipient, body=body)
        return message


class ConversationManager(models.Manager):
    def list_for_user(self, user, search_term=None):
        # List conversation list for user, provide search_term to search in messages
        if search_term:
            base = self.filter(
                Q(messages__body__icontains=search_term) | Q(messages__recipient__username__icontains=search_term),
                participants__in=[user])
        else:
            base = self.filter(participants__in=[user])

        return base.annotate(message_sent_last=Max('messages__sent_at')).order_by("-message_sent_last")

    def with_user(self, sender, recipient):
        # returns None if no conversation exists between users
        if sender == recipient:
            return None  # Self-messaging is not allowed

        users = [sender, recipient]
        conversation = self.annotate(count=Count('participants')).filter(count=2)
        for user in users:
            conversation = conversation.filter(participants__pk=user.pk)
        return conversation.first()
