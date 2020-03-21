from graphene import ObjectType

from .action import Block, Follow


class UserMutations(ObjectType):
    block = Block.Field()
    follow = Follow.Field()
