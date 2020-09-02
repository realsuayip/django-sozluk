from graphene import ObjectType

from .action import ArchiveConversation, ComposeMessage, DeleteConversation, DeleteMessage


class MessageMutations(ObjectType):
    compose = ComposeMessage.Field()
    delete = DeleteMessage.Field()
    delete_conversation = DeleteConversation.Field()
    archive_conversation = ArchiveConversation.Field()
