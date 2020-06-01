from graphene import ObjectType

from .action import ArchiveConversation, ComposeMessage, DeleteConversation


class MessageMutations(ObjectType):
    compose = ComposeMessage.Field()
    delete_conversation = DeleteConversation.Field()
    archive_conversation = ArchiveConversation.Field()
