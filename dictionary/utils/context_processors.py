import json

from contextlib import suppress
from json.decoder import JSONDecodeError
from urllib.parse import parse_qsl

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.functional import SimpleLazyObject, cached_property

from ..models import Category
from .decorators import cached_context
from .managers import TopicListManager
from .serializers import LeftFrame
from .settings import DEFAULT_CATEGORY


class LeftFrameProcessor:
    """
    Provides necessary data for left frame rendering on page load.
    """

    def __init__(self, request):
        self.user = request.user
        self.cookies = request.COOKIES

    @cached_property
    def slug(self):
        _slug = self.cookies.get("active_category")
        return _slug if _slug else DEFAULT_CATEGORY

    @cached_property
    def _page(self):
        page = self.cookies.get("navigation_page", "1")
        return int(page) if page.isdigit() else 1

    @cached_property
    def _year(self):
        return self.cookies.get("selected_year")

    @cached_property
    def _search_keys(self):
        if self.slug != "search":
            return {}

        query = self.cookies.get("search_parameters")
        return dict(parse_qsl(query)) if query else {}

    @cached_property
    def _tab(self):
        return self.cookies.get("active_tab")

    @cached_property
    def _exclusions(self):
        if exclusions := self.cookies.get("exclusions"):
            with suppress(JSONDecodeError):
                return json.loads(exclusions)
        return None

    @cached_property
    def _extra(self):
        if extra := self.cookies.get("extra"):
            with suppress(JSONDecodeError):
                return json.loads(extra)
        return {}

    def get_context(self, manager=None):
        try:
            handler = manager or TopicListManager(
                self.slug, self.user, self._year, self._search_keys, self._tab, self._exclusions, self._extra
            )

            context = LeftFrame(handler, page=self._page).as_context()
        except (Http404, PermissionDenied):
            return self.get_context(manager=TopicListManager(DEFAULT_CATEGORY))

        return context


def left_frame(request):
    frame = SimpleLazyObject(LeftFrameProcessor(request).get_context) if not request.is_mobile else {}
    return {"left_frame": frame}


@cached_context
def header_categories(_request=None):
    """
    Required for header category navigation.
    """
    categories = Category.objects.all()
    return {"nav_categories": list(categories)}
