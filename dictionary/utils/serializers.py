from contextlib import suppress

from django.core.paginator import Paginator
from django.core.serializers.json import Serializer
from django.utils.functional import cached_property

from dictionary.conf import settings
from dictionary.utils.decorators import cached_context

# Do not directly import models here

JSON_ALLOWED_OBJECTS = (dict, list, tuple, str, int, bool)


class ArchiveSerializer(Serializer):
    """
    Serializer that follows foreignkey relationships and removes model metadata.
    Credit: Arnab Kumar Shil https://ruddra.com/about/
    """

    def end_object(self, obj):
        for field in self.selected_fields:
            if field == "pk":
                continue

            if field in self._current.keys():
                continue

            with suppress(AttributeError):
                if "__" in field:
                    fields = field.split("__")
                    value = obj
                    for item in fields:
                        value = getattr(value, item)
                    if value != obj and isinstance(value, JSON_ALLOWED_OBJECTS) or value is None:
                        self._current[field] = value

        super().end_object(obj)

    def get_dump_object(self, obj):
        # Removes metadata
        return self._current


class PlainSerializer:
    """
    A surface-level 'serializer' that creates a dictionary from 'public'
    attributes.
    """

    exclude = ()
    """
    Names of attributes to be ignored while serializing.
    """

    def get_serialized(self):
        # Outer dictionary comprehension removes null values from inner dictionary.
        return {
            key: value
            for key, value in {
                name: getattr(self, name)
                for name in dir(self)
                if not name.startswith(("_", "get_serialized", "exclude") + self.exclude)
            }.items()
            if value is not None
        }


class PageSerializer(PlainSerializer):
    """Serializes page_obj of Paginator."""

    class _Paginator(PlainSerializer):
        def __init__(self, page_obj):
            self.num_pages = page_obj.paginator.num_pages
            self.page_range = tuple(page_obj.paginator.page_range)

    def __init__(self, page_obj):
        self.paginator = self._Paginator(page_obj).get_serialized()
        self.object_list = page_obj.object_list
        self.number = page_obj.number
        self.has_previous = page_obj.has_previous()
        self.has_next = page_obj.has_next()
        self.has_other_pages = page_obj.has_other_pages()

        if self.has_previous:
            self.previous_page_number = page_obj.previous_page_number()

        if self.has_next:
            self.next_page_number = page_obj.next_page_number()


class LeftFrame(PlainSerializer):
    """
    An interface for TopicListManager. (for presentation layer)
    Note: Check out PlainSerializer before you append any attribute or method.
    """

    exclude = ("as_context",)

    def __init__(self, manager, page):
        """
        :param manager: An instance of TopicListManager (or a child of TopicListHandler)
        :param page: Integer or string, for Paginator.
        """
        self.slug = manager.slug
        self._page = page
        self._manager = manager

    @cached_property
    def year_range(self):
        return settings.YEAR_RANGE if self.slug == "today-in-history" else None

    @cached_property
    def year(self):
        return self._manager.year

    @cached_property
    def safename(self):
        if overridden := self.extra.get("safename"):
            return overridden

        if self.slug in settings.NON_DB_CATEGORIES:
            return settings.NON_DB_CATEGORIES_META[self.slug][0]

        category = self.extra.get("generic_category")
        return category.name if hasattr(category, "name") else None

    @cached_property
    def slug_identifier(self):
        identifier_map = {
            **dict.fromkeys(("acquaintances", "top", "userstats"), "/entry/"),
            "drafts": "/entry/update/",
        }

        if f"{self.slug}_{self._manager.tab}" in ("userstats_channels", "acquaintances_entries"):
            return "/topic/"

        return identifier_map.get(self.slug, "/topic/")

    @cached_property
    def refresh_count(self):
        return self._manager.refresh_count

    @cached_property
    def parameters(self):
        pairs = {
            **dict.fromkeys(("today", "uncategorized", "generic"), "?a=today"),
            "popular": "?a=popular",
            "novices": "?a=novices",
            "followups": "?a=recent",
            "today-in-history": f"?a=history&year={self.year}",
            "acquaintances_entries": "?a=acquaintances&recent",
            "ama": "?a=answered",
        }

        if hasattr(self.extra.get("user_object"), "username"):
            pairs["userstats_channels"] = f"?a=search&keywords=@{self.extra.get('user_object').username}"

        key = (
            (
                param_tab  # noqa
                if self.slug in settings.TABBED_CATEGORIES
                and (param_tab := f"{self.slug}_{self._manager.tab}") in pairs
                else self.slug
            )
            if self.slug in settings.NON_DB_CATEGORIES
            else "generic"
        )

        return pairs.get(key, "")

    @cached_property
    def page(self):
        """Get current page_obj via Paginator and serialize it using PageSerializer"""
        user = self._manager.user
        paginate_by = user.topics_per_page if user.is_authenticated else settings.TOPICS_PER_PAGE_DEFAULT
        paginator = Paginator(self._manager.serialized, paginate_by)
        return PageSerializer(paginator.get_page(self._page)).get_serialized()

    @cached_property
    def tabs(self):
        if self._manager.extra.get("hidetabs") == "yes":
            return None

        tab = self._manager.tab
        if tab is not None:
            available = settings.NON_DB_CATEGORIES_META.get(self.slug)[2][0]
            return {"current": tab, "available": available}
        return None

    @cached_context
    def _get_available_exclusions(self):
        return list(settings.get_model("Category").objects_all.filter(slug__in=settings.EXCLUDABLE_CATEGORIES))

    @cached_property
    def exclusions(self):
        if self.slug == "popular":
            active = self._manager.exclusions
            available = self._get_available_exclusions()
            return {"active": active, "available": available}
        return None

    @cached_property
    def extra(self):
        return self._manager.extra

    def as_context(self):
        return self.get_serialized()
