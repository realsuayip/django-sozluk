from graphene import Mutation, String

from dictionary.models import Author, Message

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
        except Author.DoesNotExist:
            return ComposeMessage(feedback="böyle biri yok yalnız")

        sent = Message.objects.compose(sender, recipient_, body)

        if not sent:
            return ComposeMessage(feedback="mesajınızı gönderemedik ne yazık ki")

        return ComposeMessage(feedback="mesajınız sağ salim gönderildi")
