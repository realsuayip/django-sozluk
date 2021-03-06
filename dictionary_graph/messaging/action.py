from django.core.validators import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from graphene import ID, List, Mutation, String

from dictionary.conf import settings

from dictionary.models import Author, Conversation, ConversationArchive, Message
from dictionary.utils.validators import validate_user_text

from dictionary_graph.utils import login_required


class DeleteConversation(Mutation):
    class Arguments:
        mode = String()
        pk_set = List(ID)

    redirect = String()

    @staticmethod
    @login_required
    def mutate(_root, info, mode, pk_set):
        if mode not in ("archived", "present"):
            raise ValueError(_("we couldn't handle your request. try again later."))

        if mode == "present":
            model = Conversation
            url_name = "messages"
        else:
            model = ConversationArchive
            url_name = "messages-archive"

        model.objects.filter(holder=info.context.user, pk__in=pk_set).delete()
        return DeleteConversation(redirect=reverse(url_name))


class ArchiveConversation(Mutation):
    class Arguments:
        pk_set = List(ID)

    redirect = String()

    @staticmethod
    @login_required
    def mutate(_root, info, pk_set):
        conversations = (
            Conversation.objects.filter(holder=info.context.user, pk__in=pk_set)
            .select_related("holder", "target")
            .prefetch_related("messages")
        )

        for conversation in conversations:
            conversation.messages.filter(recipient=info.context.user, read_at__isnull=True).update(
                read_at=timezone.now()
            )
            conversation.archive()

        return ArchiveConversation(redirect=reverse("messages-archive"))


class ComposeMessage(Mutation):
    class Arguments:
        body = String()
        recipient = String()

    feedback = String()

    @staticmethod
    @login_required
    def mutate(_root, info, body, recipient):
        sender = info.context.user
        if len(body) < 3:
            return ComposeMessage(feedback=_("can't you write down something more?"))

        try:
            recipient_ = Author.objects.get(username=recipient)
            validate_user_text(body)
        except Author.DoesNotExist:
            return ComposeMessage(feedback=_("no such person though"))
        except ValidationError as error:
            return ComposeMessage(feedback=error.message)

        sent = Message.objects.compose(sender, recipient_, body)

        if not sent:
            return ComposeMessage(feedback=_("we couldn't send your message"))

        return ComposeMessage(feedback=_("your message has been successfully sent"))


class DeleteMessage(Mutation):
    class Arguments:
        pk = ID()

    immediate = String()

    @staticmethod
    @login_required
    def mutate(_root, info, pk):
        immediate = False
        message = Message.objects.get(pk=pk)
        conversation = message.conversation_set.get(holder=info.context.user)

        if (
            message.sender == info.context.user
            and (timezone.now() - message.sent_at).total_seconds() < settings.MESSAGE_PURGE_THRESHOLD
        ):
            # Sender deleted message immediately, remove message content for target user.
            # Translators: Include an emoji
            message.body = _("this message was deleted 🤷‍")
            message.save(update_fields=["body"])
            immediate = True

        # Delete for this user.
        conversation.messages.remove(message)

        return DeleteMessage(immediate=immediate)
