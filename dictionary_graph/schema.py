from graphene import ObjectType, Schema

from .topic.list import TopicListQuery
from .messaging.compose import ComposeMessage


class Query(TopicListQuery, ObjectType):
    # This class will inherit from multiple Queries
    # as we begin to add more apps to our project
    pass


class Mutation(ObjectType):
    # This class will include multiple Mutations
    # as we begin to add more apps to our project
    compose_message = ComposeMessage.Field()


schema = Schema(query=Query, mutation=Mutation)
