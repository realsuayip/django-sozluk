from graphene import ObjectType

from .action import Block, Follow, ToggleTheme


class UserMutations(ObjectType):
    block = Block.Field()
    follow = Follow.Field()
    toggle_theme = ToggleTheme.Field()
