from django.shortcuts import get_object_or_404
from graphene import ID, Mutation, String

from dictionary.models import Topic

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
