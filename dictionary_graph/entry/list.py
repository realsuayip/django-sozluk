from django.db.models import Q

from graphene import Int, List, ObjectType

from dictionary.models import Entry

from dictionary_graph.types import AuthorType
from dictionary_graph.utils import login_required


class EntryFavoritesQuery(ObjectType):
    favoriters = List(AuthorType, pk=Int(required=True))

    @staticmethod
    @login_required
    def resolve_favoriters(_parent, info, pk):
        return (
            Entry.objects_published.get(pk=pk)
            .favorited_by(manager="objects_accessible")
            .exclude(Q(pk__in=info.context.user.blocked.all()) | Q(pk__in=info.context.user.blocked_by.all()))
            .order_by("entryfavorites__date_created")
            .only("username", "slug", "is_novice")
        )
