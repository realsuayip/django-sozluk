from graphene import Int, List, ObjectType

from dictionary.models import Entry

from ..types import AuthorType
from ..utils import login_required


class EntryFavoritesQuery(ObjectType):
    favoriters = List(AuthorType, pk=Int(required=True))

    @staticmethod
    @login_required
    def resolve_favoriters(_, info, pk, **kwargs):
        return Entry.objects_published.get(pk=pk).favorited_by.all()
