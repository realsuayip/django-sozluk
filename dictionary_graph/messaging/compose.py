from graphene import Mutation, String

from dictionary.models import Author, Message


class ComposeMessage(Mutation):
    class Arguments:
        body = String()
        recipient = String()

    feedback = String()

    @staticmethod
    def mutate(root, info, body, recipient):
        sender = info.context.user

        if not sender.is_authenticated:
            return ComposeMessage(feedback="giriş yaparsan bu özellikten yararlanabilirsin aslında")

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
