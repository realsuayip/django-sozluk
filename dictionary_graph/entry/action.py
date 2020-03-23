from functools import wraps

from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy

from graphene import ID, Int, Mutation, String

from dictionary.models import Entry
from dictionary.utils.settings import ALLOW_ANONYMOUS_VOTING

from ..utils import AnonymousUserStorage, login_required


def owneraction(mutator):
    """Checks if sender is actually the owner of the object & gets the Entry object."""

    @wraps(mutator)
    @login_required
    def decorator(_root, info, pk):
        entry, sender = Entry.objects_all.get(pk=pk), info.context.user
        if entry.author != sender:
            raise PermissionDenied("bu aksiyonu gerçekleştirmek için gereken yetkiye sahip değilsin")
        return mutator(_root, info, entry)

    return decorator


class Action:
    """Meta clas for entry action mutations."""

    class Arguments:
        pk = ID()

    feedback = String()


class DeleteEntry(Action, Mutation):
    redirect = String()

    @staticmethod
    @owneraction
    def mutate(_root, _info, entry):
        entry.delete()
        return DeleteEntry(feedback="silindi", redirect=reverse_lazy("topic", kwargs={"slug": entry.topic.slug}))


class PinEntry(Action, Mutation):
    @staticmethod
    @owneraction
    def mutate(_root, info, entry):
        feedback = "entry sabitlendi"
        current = info.context.user.pinned_entry

        if current == entry:
            info.context.user.pinned_entry = None
            feedback = "entry artık sabit değil"
        else:
            info.context.user.pinned_entry = entry

        info.context.user.save()
        return PinEntry(feedback=feedback)


class FavoriteEntry(Action, Mutation):
    count = Int()

    @staticmethod
    @login_required
    def mutate(_root, info, pk):
        entry = Entry.objects_published.get(pk=pk)

        if info.context.user.favorite_entries.filter(pk=pk).exists():
            info.context.user.favorite_entries.remove(entry)
            return FavoriteEntry(feedback="favorilerden çıkarıldı", count=entry.favorited_by.count())

        info.context.user.favorite_entries.add(entry)
        return FavoriteEntry(feedback="favorilendi", count=entry.favorited_by.count())


def voteaction(mutator):
    """Checks if sender is actually the owner of the object, gets the Entry object. Handle anonymous votes."""

    @wraps(mutator)
    def decorator(_root, info, pk):
        entry, sender = Entry.objects_all.get(pk=pk), info.context.user

        if entry.author == sender:
            raise PermissionDenied("sen hayırdır?")

        if not sender.is_authenticated:
            if not ALLOW_ANONYMOUS_VOTING:
                raise PermissionDenied("sen hayırdır?")

            sender = AnonymousUserStorage(info.context)

        upvoted, downvoted = sender.upvoted_entries, sender.downvoted_entries
        in_upvoted, in_downvoted = upvoted.filter(pk=pk).exists(), downvoted.filter(pk=pk).exists()
        return mutator(_root, entry, upvoted, downvoted, in_upvoted, in_downvoted)

    return decorator


class UpvoteEntry(Action, Mutation):
    """Mutation to upvote an entry."""

    @staticmethod
    @voteaction
    def mutate(_root, entry, upvoted, downvoted, in_upvoted, in_downvoted):
        if in_upvoted:
            upvoted.remove(entry)  # User removes the upvote
        else:
            if in_downvoted:
                downvoted.remove(entry)  # User changes from downvote to upvote
            upvoted.add(entry)  # Usual upvote

        return UpvoteEntry(feedback="oldu")


class DownvoteEntry(Action, Mutation):
    """Mutation to downvote an entry, same logic with UpvoteEntry but reversed."""

    @staticmethod
    @voteaction
    def mutate(_root, entry, upvoted, downvoted, in_upvoted, in_downvoted):
        if in_downvoted:
            downvoted.remove(entry)
        else:
            if in_upvoted:
                upvoted.remove(entry)
            downvoted.add(entry)

        return UpvoteEntry(feedback="oldu")
