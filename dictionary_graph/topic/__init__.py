from graphene import ObjectType

from .action import FollowTopic
from .list import TopicListQuery


class TopicMutations(ObjectType):
    follow = FollowTopic.Field()


class TopicQueries(TopicListQuery):
    pass
