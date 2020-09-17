from urllib.parse import parse_qsl

from graphene import Boolean, Field, Int, JSONString, List, ObjectType, String

from dictionary.templatetags.filters import humanize_count
from dictionary.utils.managers import TopicListManager
from dictionary.utils.serializers import LeftFrame

from dictionary_graph.types import CategoryType


class Topic(ObjectType):
    title = String()
    slug = String()
    count = String()


class Paginator(ObjectType):
    num_pages = Int()
    page_range = List(Int)


class Page(ObjectType):
    has_next = Boolean()
    has_other_pages = Boolean()
    has_previous = Boolean()
    number = Int()
    object_list = List(Topic)
    paginator = Field(Paginator)


class Tab(ObjectType):
    name = String()
    safename = String()


class Exclusions(ObjectType):
    active = List(String)
    available = List(CategoryType)


class Tabs(ObjectType):
    current = String()
    available = List(Tab)


class Extra(ObjectType):
    name = String()
    value = String()


class TopicList(ObjectType):
    page = Field(Page)
    parameters = String()
    refresh_count = Int()
    year = Int()
    year_range = List(Int)
    safename = String()
    slug = String()
    slug_identifier = String()
    tabs = Field(Tabs)
    exclusions = Field(Exclusions)
    extra = List(Extra)


class TopicListQuery(ObjectType):
    topics = Field(
        TopicList,
        slug=String(required=True),
        year=Int(),
        page=Int(),
        search_keys=String(),
        refresh=Boolean(),
        tab=String(),
        exclusions=List(String),
        extra=JSONString(),
    )

    @staticmethod
    def resolve_topics(_parent, info, slug, **kwargs):
        # Convert string query parameters to actual dictionary to use it in TopicListHandler
        search_keys = dict(parse_qsl(kwargs.get("search_keys"))) if kwargs.get("search_keys") else {}
        manager = TopicListManager(
            slug,
            info.context.user,
            kwargs.get("year"),
            search_keys,
            kwargs.get("tab"),
            kwargs.get("exclusions"),
            extra=kwargs.get("extra"),
        )

        if kwargs.get("refresh"):
            manager.delete_cache(delimiter=True)

        frame = LeftFrame(manager, kwargs.get("page"))
        page = frame.page  # May raise PermissionDenied or Http404

        object_list = [
            Topic(title=t["title"], slug=t["slug"], count=humanize_count(t.get("count"))) for t in page["object_list"]
        ]

        paginator = {"num_pages": page["paginator"]["num_pages"], "page_range": page["paginator"]["page_range"]}

        tabs = (
            Tabs(
                current=frame.tabs["current"],
                available=[Tab(name=key, safename=value) for key, value in frame.tabs["available"].items()],
            )
            if frame.tabs
            else None
        )

        exclusions = (
            Exclusions(active=frame.exclusions["active"], available=frame.exclusions["available"])
            if frame.exclusions
            else None
        )

        extra = [Extra(name=key, value=value) for key, value in frame.extra.items()] if frame.extra else None

        page_data = {
            "has_next": page.get("has_next"),
            "has_other_pages": page.get("has_other_pages"),
            "has_previous": page.get("has_previous"),
            "number": page.get("number"),
            "object_list": object_list,
            "paginator": Paginator(**paginator),
        }

        data = {
            "page": Page(**page_data),
            "parameters": frame.parameters,
            "refresh_count": frame.refresh_count,
            "year": frame.year,
            "year_range": frame.year_range,
            "safename": frame.safename,
            "slug": frame.slug,
            "slug_identifier": frame.slug_identifier,
            "tabs": tabs,
            "exclusions": exclusions,
            "extra": extra,
        }

        return TopicList(**data)
