from functools import wraps

from django.db.models import Q
from graphene import Int, List, ObjectType, String

from dictionary.models import Author, Topic

from .types import AuthorType, TopicType


def autocompleter(resolver):
    """Utility decorator to validate lookup and limit arguments"""

    @wraps(resolver)
    def decorator(parent, info, lookup, limit=7, **kwargs):
        lookup, limit = lookup.strip(), limit if limit and 1 <= limit <= 7 else 7
        return resolver(parent, info, lookup, limit, **kwargs) if lookup else None

    return decorator


class AuthorAutoCompleteQuery(ObjectType):
    authors = List(AuthorType, lookup=String(required=True), limit=Int())

    @staticmethod
    @autocompleter
    def resolve_authors(parent, info, lookup, limit, **kwargs):
        return Author.objects.filter(username__istartswith=lookup, is_private=False)[:limit]


class TopicAutoCompleteQuery(ObjectType):
    topics = List(TopicType, lookup=String(required=True), limit=Int())

    @staticmethod
    @autocompleter
    def resolve_topics(parent, info, lookup, limit, **kwargs):
        return Topic.objects_published.filter(Q(title__istartswith=lookup) | Q(title__icontains=lookup),
                                              is_censored=False)[:limit]


class AutoCompleteQueries(AuthorAutoCompleteQuery, TopicAutoCompleteQuery):
    """Inherits the queries of word completion"""
