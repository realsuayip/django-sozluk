from graphene import Int, List, ObjectType, String
from graphene_django import DjangoObjectType

from dictionary.models import Author


class AuthorType(DjangoObjectType):
    class Meta:
        model = Author
        fields = ("username",)


class AuthorAutoCompleteQuery(ObjectType):
    auto_complete_author = List(AuthorType, lookup=String(required=True), limit=Int())

    @staticmethod
    def resolve_auto_complete_author(parent, info, lookup, limit=7, **kwargs):
        lookup, limit = lookup.strip(), limit if limit and 1 <= limit <= 7 else 7
        return Author.objects.filter(username__istartswith=lookup, is_private=False)[:limit] if lookup else None
