from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver

from ..messaging import Conversation, Message


@receiver(post_save, sender=Message, dispatch_uid="create_conversation")
def create_conversation(sender, instance, **kwargs):
    """
        1) Creates a conversation if user messages the other for the first time
        2) Adds messages to conversation
    """
    users = [instance.sender, instance.recipient]
    # Find conversation object for these 2 users
    conversation = Conversation.objects.annotate(count=Count('participants')).filter(count=2)
    for user in users:
        conversation = conversation.filter(participants__pk=user.pk)

    if not conversation.exists():
        conversation = Conversation.objects.create()
        conversation.participants.set([instance.sender, instance.recipient])
        conversation.messages.add(instance)
    else:
        conversation.first().messages.add(instance)
