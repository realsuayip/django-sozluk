from functools import wraps

from django.shortcuts import get_object_or_404, reverse
from graphene import Mutation, String

from dictionary.models import Author

from ..utils import login_required


def useraction(mutator):
    """Set up sender and subject, check if they are the same or subject is private. Also check for authentication."""

    @wraps(mutator)
    @login_required
    def decorator(_, info, username):
        subject, sender = get_object_or_404(Author, username=username), info.context.user
        if sender == subject or subject.is_private:
            raise ValueError("bu olmadı işte")
        return mutator(_, info, sender, subject)

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
    def mutate(root, info, sender, subject):
        if sender.blocked.filter(pk=subject.pk).exists():
            sender.blocked.remove(subject)
            return Block(feedback="engeller ortadan kalktı")

        if sender.following.filter(pk=subject.pk).exists():
            sender.following.remove(subject)

        if subject.following.filter(pk=sender.pk).exists():
            subject.following.remove(sender)

        sender.blocked.add(subject)
        return Block(feedback="engelledim gitti", redirect=info.context.build_absolute_uri(reverse("home")))


class Follow(Action, Mutation):
    @staticmethod
    @useraction
    def mutate(root, info, sender, subject):
        if subject.blocked.filter(pk=sender.pk).exists() or sender.blocked.filter(pk=subject.pk).exists():
            return Follow(feedback="olmaz")

        if sender.following.filter(pk=subject.pk).exists():
            sender.following.remove(subject)
            return Follow(feedback="takipten çıkıldı")

        sender.following.add(subject)
        return Follow(feedback="takiptesin")
