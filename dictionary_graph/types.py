from graphene_django import DjangoObjectType

from dictionary.models import Author, Topic


class AuthorType(DjangoObjectType):
    class Meta:
        model = Author
        fields = ("username", "is_novice")


class TopicType(DjangoObjectType):
    class Meta:
        model = Topic
        fields = ("title",)
