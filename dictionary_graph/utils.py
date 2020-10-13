from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from dictionary.conf import settings


def login_required(func):
    """
    Utility decorator to check if the user logged in (mutations & resolvers).
    """

    @wraps(func)
    def decorator(_root, info, *args, **kwargs):
        if not info.context.user.is_authenticated:
            raise PermissionDenied(_("actually, you may benefit from this feature by logging in."))
        return func(_root, info, *args, **kwargs)

    return decorator


class VoteStorage:
    """
    A mocking object to mock the m2m fields (upvoted_entries, downvoted_entries)
    of Author, for anonymous users.

    Anonymous users can vote, in order to hinder duplicate votes, session is
    used; though it is not the best way to handle this, I think it's better than
    storing all the IP addresses of the guest users as acquiring an IP address
    is a nuance; it depends on the server and it can also be manipulated by keen
    hackers. It's just better to stick to this way instead of making things
    complicated as there is no way to make this work 100% intended.
    """

    def __init__(self, request, name, rate):
        self.request = request
        self.name = name
        self.items = request.session.get(name, [])
        self.rate = rate

    def add(self, instance):
        self.items.append(instance.pk)
        self.request.session[self.name] = self.items
        instance.update_vote(self.rate)

    def remove(self, instance):
        self.items.remove(instance.pk)
        self.request.session[self.name] = self.items
        instance.update_vote(self.rate * -1)

    def filter(self, pk):
        return self._Filter(pk, self.items)

    class _Filter:
        def __init__(self, pk, items):
            self.pk = pk
            self.items = items

        def exists(self):
            return int(self.pk) in self.items


class AnonymousUserStorage:
    def __init__(self, request):
        self.request = request

    @property
    def upvoted_entries(self):
        return VoteStorage(self.request, name="upvoted_entries", rate=settings.VOTE_RATES["anonymous"])

    @property
    def downvoted_entries(self):
        return VoteStorage(self.request, name="downvoted_entries", rate=settings.VOTE_RATES["anonymous"] * -1)

    @property
    def is_karma_eligible(self):
        return False

    def has_exceeded_vote_limit(self, **kwargs):
        # 14 = Max allowed votes - 1
        return len(self.upvoted_entries.items) + len(self.downvoted_entries.items) > 14, None
