from graphene import Field, ObjectType, Schema

from .autocomplete import AutoCompleteQueries
from .messaging import MessageMutations
from .topic.list import TopicListQuery


class Query(TopicListQuery, ObjectType):
    # This class will include multiple Queries
    # as we begin to add more apps to our project
    autocomplete = Field(AutoCompleteQueries)

    @staticmethod
    def resolve_autocomplete(*args, **kwargs):
        return AutoCompleteQueries()


class Mutation(ObjectType):
    # This class will include multiple Mutations
    # as we begin to add more apps to our project
    message = Field(MessageMutations)

    @staticmethod
    def resolve_message(*args, **kwargs):
        return MessageMutations()


schema = Schema(query=Query, mutation=Mutation)
