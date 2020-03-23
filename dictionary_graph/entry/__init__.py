from graphene import ObjectType

from .action import DeleteEntry, DownvoteEntry, FavoriteEntry, PinEntry, UpvoteEntry
from .list import EntryFavoritesQuery


class EntryMutations(ObjectType):
    delete = DeleteEntry.Field()
    favorite = FavoriteEntry.Field()
    pin = PinEntry.Field()
    upvote = UpvoteEntry.Field()
    downvote = DownvoteEntry.Field()


class EntryQueries(EntryFavoritesQuery):
    pass
