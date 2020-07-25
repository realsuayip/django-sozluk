from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from graphene import ID, Mutation, String

from dictionary.models import Category

from ..utils import login_required


class FollowCategory(Mutation):
    class Arguments:
        pk = ID()

    feedback = String()

    @staticmethod
    @login_required
    def mutate(_root, info, pk):
        category = get_object_or_404(Category, id=pk)
        following = info.context.user.following_categories

        if following.filter(pk=pk).exists():
            following.remove(category)
            return FollowCategory(feedback=_("the channel is now followed"))

        following.add(category)
        return FollowCategory(_("the channel is no longer followed"))
