from graphene import Field, ObjectType, Schema

from .autocomplete import AutoCompleteQueries
from .category import CategoryMutations
from .entry import EntryMutations, EntryQueries
from .images import ImageMutations
from .messaging import MessageMutations
from .topic import TopicMutations, TopicQueries
from .user import UserMutations


class Query(TopicQueries, ObjectType):
    # This class will include multiple Queries
    # as we begin to add more apps to our project
    autocomplete = Field(AutoCompleteQueries)
    entry = Field(EntryQueries)

    @staticmethod
    def resolve_autocomplete(*args, **kwargs):
        return AutoCompleteQueries()

    @staticmethod
    def resolve_entry(*args, **kwargs):
        return EntryQueries()


class Mutation(ObjectType):
    # This class will include multiple Mutations
    # as we begin to add more apps to our project
    message = Field(MessageMutations)
    user = Field(UserMutations)
    topic = Field(TopicMutations)
    category = Field(CategoryMutations)
    entry = Field(EntryMutations)
    image = Field(ImageMutations)

    @staticmethod
    def resolve_message(*args, **kwargs):
        return MessageMutations()

    @staticmethod
    def resolve_user(*args, **kwargs):
        return UserMutations()

    @staticmethod
    def resolve_topic(*args, **kwargs):
        return TopicMutations()

    @staticmethod
    def resolve_category(*args, **kwargs):
        return CategoryMutations()

    @staticmethod
    def resolve_entry(*args, **kwargs):
        return EntryMutations()

    @staticmethod
    def resolve_image(*args, **kwargs):
        return ImageMutations()


schema = Schema(query=Query, mutation=Mutation)
