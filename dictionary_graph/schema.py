from graphene import Field, ObjectType, Schema

from .autocomplete import AutoCompleteQueries
from .messaging import MessageMutations
from .topic import TopicMutations, TopicQueries
from .user import UserMutations


class Query(TopicQueries, ObjectType):
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
    user = Field(UserMutations)
    topic = Field(TopicMutations)

    @staticmethod
    def resolve_message(*args, **kwargs):
        return MessageMutations()

    @staticmethod
    def resolve_user(*args, **kwargs):
        return UserMutations()

    @staticmethod
    def resolve_topic(*args, **kwargs):
        return TopicMutations()


schema = Schema(query=Query, mutation=Mutation)
