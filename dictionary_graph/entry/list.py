from graphene import Int, List, ObjectType

from dictionary.models import Entry

from ..types import AuthorType
from ..utils import login_required


class EntryFavoritesQuery(ObjectType):
    favoriters = List(AuthorType, pk=Int(required=True))

    @staticmethod
    @login_required
    def resolve_favoriters(_parent, info, pk):
        return (
            Entry.objects_published.get(pk=pk)
            .favorited_by(manager="objects_accessible")
            .exclude(pk__in=info.context.user.blocked.all())
            .order_by("entryfavorites__date_created")
        )
