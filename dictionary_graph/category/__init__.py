from graphene import ObjectType

from .action import FollowCategory, SuggestCategory


class CategoryMutations(ObjectType):
    follow = FollowCategory.Field()
    suggest = SuggestCategory.Field()
