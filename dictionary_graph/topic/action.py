from django.core.validators import ValidationError
from django.shortcuts import get_object_or_404
from graphene import ID, Mutation, String

from dictionary.models import Topic, Wish
from dictionary.templatetags.filters import formatted
from dictionary.utils import turkish_lower

from ..utils import login_required


class FollowTopic(Mutation):
    class Arguments:
        pk = ID()

    feedback = String()

    @staticmethod
    @login_required
    def mutate(_root, info, pk):
        topic = get_object_or_404(Topic, id=pk)
        following = info.context.user.following_topics

        if following.filter(pk=pk).exists():
            following.remove(topic)
            return FollowTopic(feedback="takipten çıkıldı")

        following.add(topic)
        return FollowTopic("bu başlık takipte")


class WishTopic(Mutation):
    class Arguments:
        title = String()
        hint = String()

    feedback = String()
    hint = String()

    @staticmethod
    @login_required
    def mutate(_root, info, title, hint=""):
        sender = info.context.user
        topic = Topic.objects.get_or_pseudo(unicode_string=title)
        hint = turkish_lower(hint).strip() or None

        if not topic.valid or (topic.exists and (topic.has_entries or topic.is_banned)):
            raise ValueError("öyle olmaz ki")

        wish = Wish(author=sender, hint=hint)

        try:
            wish.full_clean()
        except ValidationError as error:
            raise ValueError(", ".join(error.messages))

        if not topic.exists:
            topic = Topic.objects.create_topic(title=title)
        else:
            previous_wish = topic.wishes.filter(author=sender)
            if previous_wish.exists():
                previous_wish.delete()
                return WishTopic(feedback="ukte silindi.")

        wish.save()
        topic.wishes.add(wish)
        return WishTopic(feedback="ukteniz verildi. birileri bir şey yazarsa haber göndeririz.", hint=formatted(hint))
