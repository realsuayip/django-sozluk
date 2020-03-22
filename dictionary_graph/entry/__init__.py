from graphene import ObjectType

from .action import DeleteEntry, FavoriteEntry, PinEntry
from .list import EntryFavoritesQuery


class EntryMutations(ObjectType):
    delete = DeleteEntry.Field()
    favorite = FavoriteEntry.Field()
    pin = PinEntry.Field()


class EntryQueries(EntryFavoritesQuery):
    pass
