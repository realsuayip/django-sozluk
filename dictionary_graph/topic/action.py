from django.shortcuts import get_object_or_404
from django.template.defaultfilters import linebreaksbr
from django.utils.translation import gettext as _

from graphene import ID, Mutation, String

from dictionary.models import Topic, Wish
from dictionary.templatetags.filters import formatted
from dictionary.utils import smart_lower
from dictionary.utils.validators import validate_user_text

from dictionary_graph.utils import login_required


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

        if not sender.is_accessible:
            raise ValueError(_("sorry, the genie is now busy"))

        topic = Topic.objects.get_or_pseudo(unicode_string=title)
        hint = smart_lower(hint).strip()

        if hint:
            validate_user_text(hint, exctype=ValueError)

        if not topic.valid or (topic.exists and (topic.is_banned or topic.has_entries)):
            raise ValueError(_("we couldn't handle your request. try again later."))

        if not topic.exists:
            topic = Topic.objects.create_topic(title=title)
        else:
            previous_wish = topic.wishes.filter(author=sender)
            deleted, _types = previous_wish.delete()

            if deleted:
                return WishTopic(feedback=_("your wish has been deleted"))

        Wish.objects.create(topic=topic, author=sender, hint=hint)

        return WishTopic(
            feedback=_("your wish is now enlisted. if someone starts a discussion, we will let you know."),
            hint=linebreaksbr(formatted(hint)),
        )
