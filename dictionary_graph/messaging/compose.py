from django.core.validators import ValidationError

from graphene import Mutation, String

from dictionary.models import Author, Message
from dictionary.utils.validators import validate_user_text

from ..utils import login_required


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
            return ComposeMessage(feedback="az bir şeyler yaz yeğenim")

        try:
            recipient_ = Author.objects.get(username=recipient)
            validate_user_text(body)
        except Author.DoesNotExist:
            return ComposeMessage(feedback="böyle biri yok yalnız")
        except ValidationError as error:
            return ComposeMessage(feedback=error.message)

        sent = Message.objects.compose(sender, recipient_, body)

        if not sent:
            return ComposeMessage(feedback="mesajınızı gönderemedik ne yazık ki")

        return ComposeMessage(feedback="mesajınız sağ salim gönderildi")
