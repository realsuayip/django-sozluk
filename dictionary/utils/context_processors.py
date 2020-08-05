import json

from contextlib import suppress
from json.decoder import JSONDecodeError
from urllib.parse import parse_qsl, quote, unquote

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.functional import cached_property

from ..models import Category
from .decorators import cached_context
from .managers import TopicListManager
from .serializers import LeftFrame
from .settings import DEFAULT_CATEGORY, DEFAULT_EXCLUSIONS


class LeftFrameProcessor:
    """
    Provides necessary data for left frame rendering on page load. Validates
    cookies and handles default left frame settings.
    """

    def __init__(self, request, response):
        self.user = request.user
        self.cookies = request.COOKIES
        self.response = response

    def get_cookie(self, key):
        value = self.cookies.get(key)
        return unquote(value) if value else None

    def set_cookie(self, key, value):
        return self.response.set_cookie(key, quote(value), samesite="Lax")

    @cached_property
    def slug(self):
        _slug = self.get_cookie("lfac")
        return _slug if _slug else DEFAULT_CATEGORY

    @cached_property
    def _page(self):
        page = self.get_cookie("lfnp") or "1"
        return int(page) if page.isdigit() else 1

    @cached_property
    def _year(self):
        return self.get_cookie("lfsy")

    @cached_property
    def _search_keys(self):
        if self.slug != "search":
            return {}

        query = self.get_cookie("lfsp")
        return dict(parse_qsl(query)) if query else {}

    @cached_property
    def _tab(self):
        return self.get_cookie("lfat")

    @cached_property
    def _exclusions(self):
        if exclusions := self.get_cookie("lfex"):
            with suppress(JSONDecodeError, ValueError):
                parsed = json.loads(exclusions)
                if isinstance(parsed, list) and all(isinstance(s, str) for s in parsed):
                    return parsed
                raise ValueError

        # Returning None, handler will hit DEFAULT_EXCLUSIONS
        self.set_cookie("lfex", json.dumps(DEFAULT_EXCLUSIONS))
        return None

    @cached_property
    def _extra(self):
        if extra := self.get_cookie("lfea"):
            try:
                parsed = json.loads(extra)
                if isinstance(parsed, dict):
                    return parsed
                raise ValueError
            except (JSONDecodeError, ValueError):
                self.response.delete_cookie("lfea")
        return {}

    def get_context(self, manager=None):
        try:
            handler = manager or TopicListManager(
                self.slug, self.user, self._year, self._search_keys, self._tab, self._exclusions, self._extra
            )
            context = LeftFrame(handler, page=self._page).as_context()
        except (Http404, PermissionDenied):
            self.set_cookie("lfac", DEFAULT_CATEGORY)
            return self.get_context(manager=TopicListManager(DEFAULT_CATEGORY))

        return context


@cached_context
def header_categories(_request=None):
    """
    Required for header category navigation.
    """
    categories = Category.objects.all()
    return {"nav_categories": list(categories)}
