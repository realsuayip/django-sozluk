from django.core.validators import ValidationError
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import linebreaksbr
from django.utils.translation import gettext as _

from graphene import ID, Mutation, String

from dictionary.models import Topic, Wish
from dictionary.templatetags.filters import formatted
from dictionary.utils import smart_lower

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
            return FollowTopic(feedback=_("you no longer follow this topic"))

        following.add(topic)
        return FollowTopic(_("you are now following this topic"))


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
        hint = smart_lower(hint).strip() or None

        if not topic.valid or (topic.exists and (topic.has_entries or topic.is_banned)):
            raise ValueError(_("we couldn't handle your request. try again later."))

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
                return WishTopic(feedback=_("your wish has been deleted"))

        if not sender.is_accessible:
            raise ValueError(_("sorry, the genie is now busy"))

        wish.save()
        topic.wishes.add(wish)
        return WishTopic(
            feedback=_("your wish is now enlisted. if someone starts a discussion, we will let you know."),
            hint=linebreaksbr(formatted(hint)),
        )
