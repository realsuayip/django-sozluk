from urllib.parse import parse_qsl

from django.utils.functional import cached_property

from ..models import Category
from . import b64decode_utf8_or_none
from .decorators import cached_context
from .managers import TopicListManager
from .serializers import LeftFrame
from .settings import DEFAULT_CATEGORY, LOGIN_REQUIRED_CATEGORIES, NON_DB_CATEGORIES


class LeftFrameProcessor:
    """
    Provides necessary data for left frame rendering on page load.
    """

    def __init__(self, request):
        self.user = request.user
        self.cookies = request.COOKIES

    @cached_property
    def slug(self):
        _slug = b64decode_utf8_or_none(self.cookies.get("active_category")) or DEFAULT_CATEGORY
        unauthorized = not self.user.is_authenticated and _slug in LOGIN_REQUIRED_CATEGORIES
        not_found = _slug not in NON_DB_CATEGORIES and not Category.objects.filter(slug=_slug).exists()

        if unauthorized or not_found:
            _slug = DEFAULT_CATEGORY

        return _slug

    @cached_property
    def _page(self):
        try:
            page = int(b64decode_utf8_or_none(self.cookies.get("navigation_page")))
        except (TypeError, ValueError, OverflowError):
            page = 1

        return page

    @cached_property
    def _year(self):
        return b64decode_utf8_or_none(self.cookies.get("selected_year"))

    @cached_property
    def _search_keys(self):
        if self.slug != "hayvan-ara":
            return {}

        query = b64decode_utf8_or_none(self.cookies.get("search_parameters"))
        return dict(parse_qsl(query[1:])) if query else {}  # [1:] to omit ? from query

    def get_context(self):
        manager = TopicListManager(self.user, self.slug, self._year, self._search_keys)
        frame = LeftFrame(manager, page=self._page)
        return frame.as_context()


def left_frame(request):
    processor = LeftFrameProcessor(request)
    frame = processor.get_context()
    active_category = processor.slug
    return {"left_frame": frame, "active_category": active_category}


@cached_context
def header_categories(request):
    """
    Required for header category navigation.
    """
    categories = Category.objects.all()
    return {"nav_categories": list(categories)}
