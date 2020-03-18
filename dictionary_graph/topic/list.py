from urllib.parse import parse_qsl

from graphene import Boolean, Field, Int, List, ObjectType, String

from dictionary.utils.managers import TopicListManager
from dictionary.utils.serializers import LeftFrame


class Topic(ObjectType):
    title = String()
    slug = String()
    count = Int()


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


class TopicList(ObjectType):
    page = Field(Page)
    parameters = String()
    refresh_count = Int()
    year = Int()
    year_range = List(Int)
    safename = String()
    slug = String()
    slug_identifier = String()


class TopicListQuery(ObjectType):
    topics = Field(TopicList, slug=String(required=True), year=Int(), page=Int(), search_keys=String(),
                   refresh=Boolean())

    @staticmethod
    def resolve_topics(parent, info, slug, **kwargs):
        # Convert string query parameters to actual dicitonary to use it in TopicListHandler
        search_keys = dict(parse_qsl(kwargs.get("search_keys"))) if kwargs.get("search_keys") else {}
        manager = TopicListManager(info.context.user, slug, kwargs.get("year"), search_keys)

        if kwargs.get("refresh"):
            manager.delete_cache()

        frame = LeftFrame(manager, kwargs.get("page"))
        page = frame.page  # May raise PermissionDenied or Http404

        # @formatter:off
        object_list = [Topic(title=t['title'], slug=t['slug'], count=t.get("count")) for t in page['object_list']]

        paginator = {
            "num_pages": page['paginator']['num_pages'],
            "page_range": page['paginator']['page_range']
        }

        page_data = {
            "has_next": page.get("has_next"),
            "has_other_pages": page.get("has_other_pages"),
            "has_previous": page.get("has_previous"),
            "number": page.get("number"),
            "object_list": object_list,
            "paginator": Paginator(**paginator)
        }

        data = {
            "page": Page(**page_data),
            "parameters": frame.parameters,
            "refresh_count": frame.refresh_count,
            "year": frame.year,
            "year_range": frame.year_range,
            "safename": frame.safename,
            "slug": frame.slug,
            "slug_identifier": frame.slug_identifier
        }

        # @formatter:on
        return TopicList(**data)
