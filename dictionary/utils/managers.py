import hashlib

from decimal import Decimal
from functools import wraps
from typing import List, Union

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.db.models import CharField, Count, F, Max, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, Concat, Greatest
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from dateutil.relativedelta import relativedelta

from ..models import Author, Category, DownvotedEntries, Entry, Topic, UpvotedEntries
from ..utils import parse_date_or_none, time_threshold
from ..utils.decorators import for_public_methods
from ..utils.settings import (
    DEFAULT_CACHE_TIMEOUT,
    DISABLE_CATEGORY_CACHING,
    EXCLUDABLE_CATEGORIES,
    EXCLUSIVE_TIMEOUTS,
    LOGIN_REQUIRED_CATEGORIES,
    NON_DB_CATEGORIES,
    NON_DB_CATEGORIES_META,
    PARAMETRIC_CATEGORIES,
    TABBED_CATEGORIES,
    TOPICS_PER_PAGE_DEFAULT,
    UNCACHED_CATEGORIES,
    USER_EXCLUSIVE_CATEGORIES,
    YEAR_RANGE,
)


class TopicQueryHandler:
    """
    Queryset algorithms for topic lists.
    Each non-database category has its own method, note that function names correspond to their slugs, this allows
    us to write a clean code, and each time we have to edit one of them for specific feature it won't be painful.
    """

    # Queryset filters
    day_filter = {"entries__date_created__gte": time_threshold(hours=24)}
    base_filter = {"entries__is_draft": False, "entries__author__is_novice": False, "is_censored": False}

    # Queryset annotations
    base_annotation = {"latest": Max("entries__date_created")}  # to order_by("-latest")
    base_count = {"count": Count("entries", filter=Q(**day_filter))}

    # Queryset values
    values = ("title", "slug", "count")
    values_entry = values[:2]  # values with count excluded (used for entry listing)

    def today(self, user):
        return (
            Topic.objects.filter(
                Q(category__in=user.following_categories.all()) | Q(category=None),
                **self.base_filter,
                **self.day_filter,
            )
            .order_by("-latest")
            .annotate(**self.base_annotation, **self.base_count)
            .exclude(created_by__in=user.blocked.all())
            .values(*self.values)
        )

    def today_in_history(self, year):
        now = timezone.now()
        diff = now.year - year
        delta = now - relativedelta(years=diff)
        return (
            Topic.objects.filter(**self.base_filter, entries__date_created__date=delta.date())
            .annotate(count=Count("entries"))
            .order_by("-count")
            .values(*self.values)
        )

    def popular(self, exclusions):
        def counter(hours):
            return Count("entries", filter=Q(entries__date_created__gte=time_threshold(hours=hours)))

        return (
            Topic.objects.filter(**self.base_filter)
            .annotate(**self.base_count)
            .filter(Q(count__gte=10) | Q(is_pinned=True))
            .exclude(category__slug__in=exclusions)
            .annotate(q1=counter(3), q2=counter(6), q3=counter(12), **self.base_annotation)
            .order_by("-is_pinned", "-q1", "-q2", "-q3", "-count", "-latest")
            .values(*self.values)
        )

    def top(self, tab):
        filters = {
            "yesterday": {"date_created__date": time_threshold(hours=24).date()},
            "week": {"date_created__lte": time_threshold(days=7), "date_created__gte": time_threshold(days=14)},
        }
        return (
            Entry.objects.filter(**filters.get(tab), topic__is_censored=False)
            .order_by("-vote_rate")
            .annotate(title=F("topic__title"), slug=F("pk"))
            .values(*self.values_entry)
        )[:TOPICS_PER_PAGE_DEFAULT]

    def drafts(self, user):
        return (
            Entry.objects_all.filter(author=user, is_draft=True)
            .order_by("-date_created")
            .annotate(title=F("topic__title"), slug=F("pk"))
            .values(*self.values_entry)
        )

    def acquaintances(self, user, tab):
        return getattr(self, f"acquaintances_{tab}")(user)

    def acquaintances_entries(self, user):
        return (
            Entry.objects.filter(date_created__gte=time_threshold(hours=24), author__in=user.following.all())
            .order_by("-date_created")
            .annotate(title=Concat(F("topic__title"), Value(" (@"), F("author__username"), Value(")")), slug=F("pk"))
            .values(*self.values_entry)
        )

    def acquaintances_favorites(self, user):
        return (
            Entry.objects.filter(
                favorited_by__in=user.following.all(), entryfavorites__date_created__gte=time_threshold(hours=24)
            )
            .annotate(
                title=Concat(F("topic__title"), Value(" (#"), F("pk"), Value(")"), output_field=CharField()),
                slug=F("pk"),
                latest=Max("entryfavorites__date_created"),
            )
            .order_by("-latest")
            .values(*self.values_entry)
        )

    def wishes(self, user, tab):
        return getattr(self, f"wishes_{tab}")(user)

    def wishes_all(self, user):
        return (
            Topic.objects.exclude(wishes__author__in=user.blocked.all())
            .annotate(count=Count("wishes"), latest=Max("wishes__date_created"))
            .filter(count__gte=1)
            .order_by("-count", "-latest")
        ).values(*self.values)

    def wishes_owned(self, user):
        return (
            Topic.objects.filter(wishes__author=user)
            .annotate(count=Count("wishes"), latest=Max("wishes__date_created"))
            .order_by("-latest")
        ).values(*self.values)

    def followups(self, user):
        """
        Author: Emre Tuna (https://github.com/emretuna01) <emretuna@outlook.com>

        todo: If you can convert this to native orm or create a queryset that will result in same data, please do.
        I tried to make the sql easy-to-read, but failed as there were many aliases that I couldn't find a meaningful
        name. They are named arbitrarily, if you think you can make it more readable, please do.

        Query Description: List topics on condition that the user has entries in in (written in last 24 hours), along
        with count of entries that were written after the user's latest entry on that topic.
        """

        pk = user.pk
        threshold = time_threshold(hours=120)  # in 5 days

        with connection.cursor() as cursor:
            cursor.execute(
                """
            select
              s.title,
              s.slug,
              s.count
            from
              (
                select
                  tt.title,
                  tt.slug,
                  e.count,
                  e.max_id
                from
                  (
                    select
                      z.topic_id,
                      count(
                        case
                        when z.id > k.max_id
                        and not z.is_draft
                        and z.author_id not in (
                          select to_author_id
                          from dictionary_author_blocked
                          where from_author_id = k.sender_id
                        )
                        and case
                            when not k.sender_is_novice then
                            not (select is_novice from dictionary_author where id = z.author_id)
                            else true end
                        then z.id end
                      ) as count,
                      k.max_id
                    from
                      dictionary_entry z
                      inner join (
                        select
                          topic_id,
                          max(de.id) as max_id,
                          de.author_id as sender_id,
                          (select is_novice from dictionary_author where id = de.author_id) as sender_is_novice
                        from
                          dictionary_entry de
                        where
                          de.date_created >= %s
                          and de.author_id = %s
                        group by
                          author_id,
                          topic_id
                      ) k on k.topic_id = z.topic_id
                    group by
                      z.topic_id,
                      k.max_id
                  ) e
                  inner join dictionary_topic tt on tt.id = e.topic_id
              ) s
            where
              s.count > 0
            order by
              s.max_id desc
            """,
                [threshold, pk],
            )

            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def novices(self):
        caylak_filter = {"entries__author__is_novice": True, "entries__is_draft": False, "is_censored": False}
        return (
            Topic.objects.filter(**self.day_filter, **caylak_filter)
            .order_by("-latest")
            .annotate(**self.base_annotation, **self.base_count)
            .values(*self.values)
        )

    def search(self, user, search_keys):
        """
        The logic of advanced search feature.
        Notice: If you are including a new field, and it requires an annotation, you will need to use SubQuery.
        Notice: Entry counts given in accordance with search filters, it may not be the count of ALL entries.
        """

        keywords = search_keys.get("keywords")
        author_nick = search_keys.get("author_nick")
        favorites_only = search_keys.get("is_in_favorites") == "true"
        nice_only = search_keys.get("is_nice_ones") == "true"
        from_date = search_keys.get("from_date")
        to_date = search_keys.get("to_date")
        orderding = search_keys.get("ordering")

        # Input validation
        from_date = parse_date_or_none(from_date, dayfirst=False)
        to_date = parse_date_or_none(to_date, dayfirst=False)

        if orderding not in ("alpha", "newer", "popular"):
            orderding = "newer"

        # Provide a default search term if none present
        if not keywords and not author_nick and not (favorites_only and user.is_authenticated):
            keywords = "akıl fikir"

        filters = {}

        # Filtering
        if favorites_only and user.is_authenticated:
            filters["entries__favorited_by"] = user

        # Originally this would sum up all the entries' rates, but in new implementation it considers only one entry
        # Summing up all entries requires SubQueries and it complicates things a lot. This filter is decent anyway.
        if nice_only:
            filters["entries__vote_rate__gte"] = Decimal("489")

        if author_nick:
            filters["entries__author__username"] = author_nick

        if keywords:
            filters["title__icontains"] = keywords

        if from_date:
            filters["entries__date_created__gte"] = from_date

        if to_date:
            filters["entries__date_created__lte"] = to_date

        qs = Topic.objects.filter(**self.base_filter, **filters).annotate(count=Count("entries", distinct=True))
        ordering_map = {"alpha": ["title"], "newer": ["-date_created"], "popular": ["-count", "-date_created"]}
        result = qs.order_by(*ordering_map.get(orderding)).values(*self.values)[:TOPICS_PER_PAGE_DEFAULT]
        return result

    def generic_category(self, slug):
        category = get_object_or_404(Category, slug=slug)
        return (
            Topic.objects.filter(**self.base_filter, **self.day_filter, category=category)
            .order_by("-latest")
            .annotate(**self.base_annotation, **self.base_count)
            .values(*self.values)
        )

    def uncategorized(self):
        return (
            Topic.objects.filter(**self.base_filter, **self.day_filter, category=None)
            .order_by("-latest")
            .annotate(**self.base_annotation, **self.base_count)
            .values(*self.values)
        )

    def userstats(self, username, channel, tab):
        if not username:
            raise Http404

        user = get_object_or_404(Author, username=username)

        if tab == "channels":
            return self.userstats_channels(user, channel)

        handler = UserStatsQueryHandler(user)
        return (
            getattr(handler, tab)()
            .annotate(title=F("topic__title"), slug=F("pk"))
            .order_by(handler.order_map.get(tab))
            .values(*self.values_entry)
        )

    def userstats_channels(self, user, channel):
        category = get_object_or_404(Category, name=channel)
        return (
            Topic.objects.filter(entries__author=user, entries__is_draft=False, category=category)
            .annotate(
                count=Count("entries"),
                latest_entry=Subquery(
                    Entry.objects.filter(topic=OuterRef("pk")).order_by("-date_created").values("date_created")[:1]
                ),
            )
            .order_by("-latest_entry")
            .values(*self.values)
        )


class TopicListHandler:
    """
    Handles given topic slug and finds corresponding method in TopicQueryHandler to serialize data. Caches topic lists.
    Handles authentication and validation.
    """

    data = None
    cache_exists = False
    cache_key = None

    _available_extras = ("user", "channel")
    """Available external extras."""

    _extras_cache_per = ("user", "channel")
    """Include the value of these extras in cache key."""

    def __init__(
        self,
        slug: str,
        user: Union[Author, AnonymousUser] = AnonymousUser(),
        year: Union[str, int] = None,
        search_keys: dict = None,
        tab: str = None,
        exclusions: List[str] = None,
        extra: dict = None,
    ):
        """
        :param user: User requesting the list. Used for topics per page and checking login requirements.
        :param slug: Slug of the category.
        :param year: Required for today-in-history.
        :param search_keys: Search keys for "search" (advanced search).
        :param tab: Tab name for tabbed categories.
        :param exclusions: List of category slugs to be excluded in popular.
        :param extra: Any other metadata about the slug.
        """

        if not user.is_authenticated and slug in LOGIN_REQUIRED_CATEGORIES:
            raise PermissionDenied("User not logged in")

        self.slug = slug
        self.user = user

        self.year = self._validate_year(year)
        self.tab = self._validate_tab(tab)
        self.exclusions = self._validate_exclusions(exclusions)
        self.search_keys = search_keys if self.slug == "search" else {}
        self.extra = self._validate_extra(extra)

        self._set_internal_extra()

        # Check cache
        if self._caching_allowed:
            self._check_cache()

    def _get_data(self):
        """No cache found, prepare the query. (serialized hits the db)"""

        # Arguments to be passed for TopicQueryHandler methods.
        arg_map = {
            **dict.fromkeys(("today", "drafts", "followups"), [self.user]),
            **dict.fromkeys(("acquaintances", "wishes"), [self.user, self.tab]),
            "today_in_history": [self.year],
            "generic_category": [self.slug],
            "search": [self.user, self.search_keys],
            "popular": [self.exclusions],
            "top": [self.tab],
            "userstats": [self.extra.get("user"), self.extra.get("channel"), self.tab],
        }

        # Convert today-in-history => today_in_history
        slug_method = self.slug.replace("-", "_") if self.slug in NON_DB_CATEGORIES else "generic_category"

        # Get the method from TopicQueryHandler.
        return getattr(self, slug_method)(*arg_map.get(slug_method, []))

    def _validate_exclusions(self, exclusions):
        return (
            tuple(slug for slug in exclusions if slug in EXCLUDABLE_CATEGORIES)
            if self.slug == "popular" and exclusions is not None
            else ()
        )

    def _validate_tab(self, tab):
        if self.slug in TABBED_CATEGORIES:
            tab_meta = NON_DB_CATEGORIES_META.get(self.slug)[2]
            avaiable_tabs, default_tab = tab_meta[0].keys(), tab_meta[1]
            return tab if tab in avaiable_tabs else default_tab
        return None

    def _validate_year(self, year):
        """Validates and sets the year."""
        if self.slug == "today-in-history":
            default = 2020
            if year is not None:

                if not isinstance(year, (str, int)):
                    raise TypeError("The year either needs to be an integer or a string.")

                if isinstance(year, str):
                    year = int(year) if year.isdigit() else default

                return year if year in YEAR_RANGE else default

            return default
        return None

    def _validate_extra(self, extra):
        return (
            {key: value for key, value in extra.items() if key in self._available_extras and isinstance(value, str)}
            if extra and self.slug in PARAMETRIC_CATEGORIES
            else {}
        )

    def _set_internal_extra(self):
        """
        Set internal extras to change the default behaviour.
        The slug doesn't need to be in parameteric categories.
        """

        if self.slug == "userstats":
            fmtstr = [self.extra.get("user")]

            if self.tab == "channels":
                fmtstr.append(self.extra.get("channel"))
            else:
                self.extra.pop("channel", None)  # so as not to interfere with cache key

            self.extra["safename"] = NON_DB_CATEGORIES_META["userstats"][2][0][self.tab].format(*fmtstr)
            self.extra["hidetabs"] = "yes"

    @property
    def _caching_allowed(self):
        return not (
            self.slug in UNCACHED_CATEGORIES
            or f"{self.slug}_{self.tab}" in UNCACHED_CATEGORIES
            or DISABLE_CATEGORY_CACHING
        )

    def _cache_data(self, data):
        if self._caching_allowed:
            cache.set(
                self.cache_key,
                {"data": data, "set_at": timezone.now()},
                EXCLUSIVE_TIMEOUTS.get(self.slug, DEFAULT_CACHE_TIMEOUT),
            )
        return data

    def _create_cache_key(self):
        private = f"private_uid_{self.user.id}"
        public = "public"

        scope = private if self.slug in USER_EXCLUSIVE_CATEGORIES else public
        year = self.year or ""
        tab = ":t:" + self.tab if self.tab else ""
        search_keys = ""
        exclusions = "_".join(sorted(self.exclusions)) if self.exclusions else ""
        extra = (
            ":x:"
            + "_".join(f"{key}={value}" for key, value in sorted(self.extra.items()) if key in self._extras_cache_per)
            if self.extra
            else ""
        )

        if self.slug == "search":
            # Create special hashed suffix for search parameters
            available_search_params = (
                "keywords",
                "author_nick",
                "is_in_favorites",
                "is_nice_ones",
                "from_date",
                "to_date",
                "ordering",
            )

            params = {param: self.search_keys.get(param, "_") for param in available_search_params}

            if params["is_in_favorites"] != "_":
                scope = private

            search_keys = hashlib.blake2b("".join(params.values()).encode("utf-8")).hexdigest()

        self.cache_key = f"tlq_{scope}_{self.slug}{year}{tab}{search_keys}{exclusions}{extra}"

    def _check_cache(self):
        self._create_cache_key()
        cached_data = cache.get(self.cache_key)

        if cached_data is not None:
            if self.slug in ("top", "today-in-history"):
                # check if the day has changed or not for top or today-in-history
                if cached_data.get("set_at").day == timezone.now().day:
                    self.cache_exists = True
            else:
                self.cache_exists = True

    def delete_cache(self, flush=False):
        """
        Deletes cached data and initiates new data using _get_data.
        Call this before serialized to get new results.
        :param flush: Set this to true if you don't need new data.
        """
        if self.cache_exists:
            cache.delete(self.cache_key)
            self.cache_exists = False

            if flush:
                self.data = ()  # empty tuple

            return True
        return False

    @property
    def _cached_data(self):
        return cache.get(self.cache_key).get("data")

    @property
    def serialized(self):
        # Serialize topic queryset data, cache it and return it.
        if self.cache_exists:
            return self._cached_data

        if self.data is None:
            self.data = self._get_data()

        # Notice: caching the queryset will evaluate it anyway
        return self._cache_data(tuple(self.data))

    @property
    def slug_identifier(self):
        # todo: move this to LeftFrame and refactor it to be like parameters
        if f"{self.slug}_{self.tab}" == "userstats_channels":
            return "/topic/"

        if self.slug in ("acquaintances", "top", "userstats"):
            return "/entry/"

        if self.slug == "drafts":
            return "/entry/update/"

        return "/topic/"

    @property
    def refresh_count(self):  # (yenile count)
        if self.cache_exists and self.slug == "today":
            set_at = cache.get(self.cache_key).get("set_at")
            return Entry.objects.filter(date_created__gte=set_at).count()

        return 0


class TopicListManager(TopicListHandler, TopicQueryHandler):
    """
    Responsible for topic list management at the back-end level.
    Whenever a topic list is called, this manager is behind it.
    """


def conditional_ordering(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        result = method(self, *args, **kwargs)
        if self.order and method.__name__ in self.order_map:
            return result.order_by(self.order_map.get(method.__name__))
        return result

    return wrapped


@for_public_methods(conditional_ordering)
class UserStatsQueryHandler:
    """Queries for user stats on profile page."""

    order_map = {
        "latest": "-date_created",
        "favorites": "-entryfavorites__date_created",
        "popular": "-count",
        "liked": "-vote_rate",
        "weeklygoods": "-vote_rate",
        "beloved": "-date_created",
        "recentlyvoted": "-last_voted",
    }

    def __init__(self, user, order=False):
        self.user = user
        self.entries = user.entry_set(manager="objects_published")
        self.order = order

    def latest(self):
        return self.entries.all()

    def favorites(self):
        return self.user.favorite_entries.filter(author__is_novice=False)

    def popular(self):
        return self.entries.annotate(count=Count("favorited_by")).filter(count__gte=1)

    def liked(self):
        return self.entries.filter(vote_rate__gt=0)

    def weeklygoods(self):
        return self.entries.filter(vote_rate__gt=0, date_created__gte=time_threshold(days=7))

    def beloved(self):
        return self.entries.filter(favorited_by__in=[self.user])

    def recentlyvoted(self):
        up, down = (
            Subquery(model.objects.filter(entry=OuterRef("pk")).order_by("-date_created").values("date_created")[:1])
            for model in (UpvotedEntries, DownvotedEntries)
        )

        return self.entries.annotate(last_voted=Coalesce(Greatest(up, down), up, down)).filter(last_voted__isnull=False)

    def wishes(self):
        return (
            Topic.objects.filter(wishes__author=self.user)
            .annotate(latest=Max("wishes__date_created"))
            .only("title", "slug")
            .order_by("-latest")
        )

    def channels(self):
        return (
            Category.objects.annotate(
                count=Count(
                    "topic__entries", filter=Q(topic__entries__author=self.user, topic__entries__is_draft=False)
                )
            )
            .filter(count__gte=1)
            .order_by("-count")
        )

    def authors(self):
        return (
            Author.objects_accessible.filter(entry__in=self.user.favorite_entries.all())
            .annotate(frequency=Count("entry"))
            .filter(frequency__gt=1)
            .exclude(Q(pk=self.user.pk) | Q(blocked__in=[self.user.pk]) | Q(pk__in=self.user.blocked.all()))
            .only("username", "slug")
            .order_by("-frequency")[:10]
        )
