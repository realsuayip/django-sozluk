from functools import wraps

from django.shortcuts import get_object_or_404, reverse
from django.utils.translation import gettext as _

from graphene import Mutation, String

from dictionary.models import Author

from dictionary_graph.utils import login_required


def useraction(mutator):
    """
    Set up sender and subject, check if they are the same or subject is private.
    Also check for authentication.
    """

    @wraps(mutator)
    @login_required
    def decorator(_root, info, username):
        subject, sender = get_object_or_404(Author, username=username), info.context.user
        if sender == subject or subject.is_private:
            raise ValueError(_("we couldn't handle your request. try again later."))
        return mutator(_root, info, sender, subject)

    return decorator


class Action:
    """Meta class for action Mutations"""

    class Arguments:
        username = String()

    feedback = String()
    redirect = String()


class Block(Action, Mutation):
    @staticmethod
    @useraction
    def mutate(_root, info, sender, subject):
        if sender.blocked.filter(pk=subject.pk).exists():
            sender.blocked.remove(subject)
            return Block(feedback=_("removed blockages"))

        sender.following.remove(subject)
        subject.following.remove(sender)
        sender.blocked.add(subject)
        sender.favorite_entries.remove(*sender.favorite_entries.filter(author__in=[subject]))
        return Block(feedback=_("the person is now blocked"), redirect=info.context.build_absolute_uri(reverse("home")))


class Follow(Action, Mutation):
    @staticmethod
    @useraction
    def mutate(_root, _info, sender, subject):
        if (
            subject.is_hidden
            or subject.blocked.filter(pk=sender.pk).exists()
            or sender.blocked.filter(pk=subject.pk).exists()
        ):
            return Follow(feedback=_("we couldn't handle your request. try again later."))

        if sender.following.filter(pk=subject.pk).exists():
            sender.following.remove(subject)
            return Follow(feedback=_("you no longer follow this person"))

        sender.following.add(subject)
        return Follow(feedback=_("you are now following this user"))


class ToggleTheme(Mutation):
    """Toggles theme for logged in users."""
    theme = String()

    @staticmethod
    @login_required
    def mutate(_root, info):
        user = info.context.user
        if user.theme == Author.Theme.DARK:
            user.theme = Author.Theme.LIGHT
            user.save(update_fields=["theme"])
            return ToggleTheme(user.theme)

        user.theme = Author.Theme.DARK
        user.save(update_fields=["theme"])
        return ToggleTheme(user.theme)
