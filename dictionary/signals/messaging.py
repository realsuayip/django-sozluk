from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver

from dictionary.models.messaging import Conversation, Message


@receiver(post_save, sender=Message, dispatch_uid="deliver_message")
def deliver_message(instance, created, **kwargs):
    """
    Creates a conversation if user messages the other for the first time.
    Adds messages to conversation.
    """

    if not created:
        return

    holder, _ = instance.sender.conversations.get_or_create(target=instance.recipient)
    target, _ = instance.recipient.conversations.get_or_create(target=instance.sender)

    holder.messages.add(instance)
    target.messages.add(instance)


@receiver(m2m_changed, sender=Conversation.messages.through)
def delete_orphan_messages_individual(action, pk_set, **kwargs):
    if action == "post_remove" and not Conversation.objects.filter(messages__in=pk_set).exists():
        Message.objects.filter(pk__in=pk_set).delete()


@receiver(pre_delete, sender=Conversation)
def delete_orphan_messages_bulk(instance, **kwargs):
    instance.messages.remove(*instance.messages.all())
