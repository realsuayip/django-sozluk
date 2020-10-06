from functools import wraps

from django.db.models import Q
from graphene import Int, List, ObjectType, String

from dictionary.models import Author, Topic

from dictionary_graph.types import AuthorType, TopicType


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
    def resolve_authors(_parent, info, lookup, limit):
        queryset = Author.objects_accessible.filter(username__istartswith=lookup).only("username", "slug", "is_novice")

        if info.context.user.is_authenticated:
            blocked = info.context.user.blocked.all()
            blocked_by = info.context.user.blocked_by.all()
            return queryset.exclude(Q(pk__in=blocked) | Q(pk__in=blocked_by))[:limit]

        return queryset[:limit]


class TopicAutoCompleteQuery(ObjectType):
    topics = List(TopicType, lookup=String(required=True), limit=Int())

    @staticmethod
    @autocompleter
    def resolve_topics(_parent, _info, lookup, limit):
        return Topic.objects_published.filter(
            Q(title__istartswith=lookup) | Q(title__icontains=lookup), is_censored=False
        ).only("title")[:limit]


class AutoCompleteQueries(AuthorAutoCompleteQuery, TopicAutoCompleteQuery):
    """Inherits the queries of word completion"""
