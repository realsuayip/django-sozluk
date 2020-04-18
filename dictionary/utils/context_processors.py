import json
from urllib.parse import parse_qsl

from django.utils.functional import cached_property

from ..models import Category
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
        _slug = self.cookies.get("active_category") or DEFAULT_CATEGORY
        unauthorized = not self.user.is_authenticated and _slug in LOGIN_REQUIRED_CATEGORIES
        not_found = _slug not in NON_DB_CATEGORIES and not Category.objects.filter(slug=_slug).exists()

        if unauthorized or not_found:
            _slug = DEFAULT_CATEGORY

        return _slug

    @cached_property
    def _page(self):
        page = self.cookies.get("navigation_page", "1")
        return int(page) if page.isdigit() else 1

    @cached_property
    def _year(self):
        return self.cookies.get("selected_year")

    @cached_property
    def _search_keys(self):
        if self.slug != "hayvan-ara":
            return {}

        query = self.cookies.get("search_parameters")
        return dict(parse_qsl(query)) if query else {}

    @cached_property
    def _tab(self):
        return self.cookies.get("active_tab")

    @cached_property
    def _exclusions(self):
        exclusions = self.cookies.get("exclusions")
        return [slug for slug in json.loads(exclusions) if isinstance(slug, str)] if exclusions else None

    def get_context(self):
        manager = TopicListManager(self.slug, self.user, self._year, self._search_keys, self._tab, self._exclusions)
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
