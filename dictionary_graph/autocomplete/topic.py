from django.db.models import Q
from graphene import Int, List, ObjectType, String
from graphene_django import DjangoObjectType

from dictionary.models import Topic


class TopicType(DjangoObjectType):
    class Meta:
        model = Topic
        fields = ("title",)


class TopicAutoCompleteQuery(ObjectType):
    auto_complete_topic = List(TopicType, lookup=String(required=True), limit=Int())

    @staticmethod
    def resolve_auto_complete_topic(parent, info, lookup, limit=7, **kwargs):
        lookup, limit = lookup.strip(), limit if limit and 1 <= limit <= 7 else 7
        return Topic.objects_published.filter(Q(title__istartswith=lookup) | Q(title__icontains=lookup),
                                              is_censored=False)[:limit] if lookup else None
