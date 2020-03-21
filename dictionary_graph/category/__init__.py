from graphene import ObjectType

from .action import FollowCategory


class CategoryMutations(ObjectType):
    follow = FollowCategory.Field()
