from graphene import ObjectType

from .compose import ComposeMessage


class MessageMutations(ObjectType):
    compose = ComposeMessage.Field()
