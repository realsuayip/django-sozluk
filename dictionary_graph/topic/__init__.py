from graphene import ObjectType

from .action import FollowTopic, WishTopic
from .list import TopicListQuery


class TopicMutations(ObjectType):
    follow = FollowTopic.Field()
    wish = WishTopic.Field()


class TopicQueries(TopicListQuery):
    pass
