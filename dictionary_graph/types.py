from graphene_django import DjangoObjectType

from dictionary.models import Author, Category, Topic


class AuthorType(DjangoObjectType):
    class Meta:
        model = Author
        fields = ("username", "slug", "is_novice")


class TopicType(DjangoObjectType):
    class Meta:
        model = Topic
        fields = ("title",)


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ("name", "slug", "description")
