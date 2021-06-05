import hashlib

from decimal import Decimal
from functools import wraps
from typing import List, Union

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.db.models import CharField, Count, Exists, F, Max, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce, Concat, Greatest
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _

from dateutil.relativedelta import relativedelta

from dictionary.conf import settings
from dictionary.models import Author, Category, Comment, DownvotedEntries, Entry, EntryFavorites, Topic, UpvotedEntries
from dictionary.utils import parse_date_or_none, time_threshold
from dictionary.utils.decorators import for_public_methods


class TopicQueryHandler:
    """
    Queryset algorithms for topic lists. Each non-database category has its own
    method and their names correspond to their slugs, this allows for clean code.
    """

    # Queryset filters
    @property
    def day_filter(self):
        return {"entries__date_created__gte": time_threshold(hours=24)}

    base_filter = {"entries__is_draft": False, "entries__author__is_novice": False, "is_censored": False}

    # Queryset annotations
    latest = {"latest": Max("entries__date_created")}  # to order_by("-latest")

    # Queryset values
    values = ("title", "slug")

    def today(self, user):
        categories = Q(category__in=user.following_categories.all())

        if user.allow_uncategorized:
            categories |= Q(category=None)

        return (
            Topic.objects.values(*self.values)
            .filter(**self.base_filter, **self.day_filter)
            .filter(categories)
            .exclude(created_by__in=user.blocked.all())
            .annotate(**self.latest, count=Count("entries", distinct=True))
            .order_by("-latest")
        )

    def today_in_history(self, year):
        now = timezone.now()
        diff = now.year - year
        # If we don't use localtime, date() may shift a day because of the hour difference.
        delta = timezone.localtime(now - relativedelta(years=diff))

        return (
            Topic.objects.values(*self.values)
            .filter(**self.base_filter, entries__date_created__date=delta.date())
            .annotate(count=Count("entries"))
            .order_by("-count")
        )

    def popular(self, exclusions):
        def counter(hours):
            return Count("entries", filter=Q(entries__date_created__gte=time_threshold(hours=hours)))

        return (
            Topic.objects.values(*self.values)
            .filter(**self.base_filter)
            .annotate(count=Count("entries", filter=Q(**self.day_filter)))
            .filter(Q(count__gte=10) | Q(is_pinned=True))
            .exclude(category__slug__in=exclusions)
            .alias(q1=counter(3), q2=counter(6), q3=counter(12), **self.latest)
            .order_by("-is_pinned", "-q1", "-q2", "-q3", "-count", "-latest")
        )

    def top(self, tab):
        filters = {
            "yesterday": {"date_created__date": timezone.localtime(time_threshold(hours=24)).date()},
            "week": {"date_created__lte": time_threshold(days=7), "date_created__gte": time_threshold(days=14)},
        }
        return (
            Entry.objects.filter(**filters.get(tab), vote_rate__gt=0, topic__is_censored=False)
            .order_by("-vote_rate")
            .annotate(title=F("topic__title"), slug=F("pk"))
            .values(*self.values)
        )[: settings.TOPICS_PER_PAGE_DEFAULT]

    def drafts(self, user):
        return (
            Entry.objects_all.filter(author=user, is_draft=True)
            .order_by("-date_created")
            .annotate(title=F("topic__title"), slug=F("pk"))
            .values(*self.values)
        )

    def acquaintances(self, user, tab):
        return getattr(self, f"acquaintances_{tab}")(user)

    def acquaintances_entries(self, user):
        return (
            Topic.objects.values(*self.values)
            .filter(
                entries__is_draft=False,
                entries__date_created__gte=time_threshold(hours=120),
                entries__author__in=user.following.all(),
            )
            .annotate(latest=Max("entries__date_created"), count=Count("entries"))
            .order_by("-latest")
        )

    def acquaintances_favorites(self, user):
        return (
            Entry.objects_published.values("topic")
            .filter(favorited_by__in=user.following.all(), entryfavorites__date_created__gte=time_threshold(hours=24))
            .annotate(
                title=Concat(F("topic__title"), Value(" (#"), F("pk"), Value(")"), output_field=CharField()),
                slug=F("pk"),
                latest=Max("entryfavorites__date_created"),
            )
            .order_by("-latest")
            .values(*self.values)
        )

    def wishes(self, user, tab):
        return getattr(self, f"wishes_{tab}")(user)

    def wishes_all(self, user):
        return (
            Topic.objects.values(*self.values)
            .exclude(wishes__author__in=user.blocked.all())
            .annotate(count=Count("wishes"), latest=Max("wishes__date_created"))
            .filter(is_censored=False, count__gte=1)
            .order_by("-count", "-latest")
        )

    def wishes_owned(self, user):
        return (
            Topic.objects.values(*self.values)
            .filter(wishes__author=user)
            .annotate(count=Count("wishes"), latest=Max("wishes__date_created"))
            .order_by("-latest")
        )

    def followups(self, user):  # noqa
        """
        Author: Emre Tuna (https://github.com/emretuna01) <emretuna@outlook.com>

        todo: If you can convert this to native orm or create a queryset that will result in same data, please do.
        Update: An ORM implementation was made, but it was too slow compared to
        this solution. See: https://gist.github.com/realsuayip/9d2c5365cbe6e43d1fe282a556d0f6d5

        I tried to make the sql easy-to-read, but failed as there were many
        aliases that I couldn't find meaningful names. They are named arbitrarily,
        if you think you can make it more readable, please do.

        Query Description: List topics on condition that the user has entries in
        (written in last 24 hours), along with count of entries that were
        written after the user's latest entry on that topic.
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
        return (
            Topic.objects.values(*self.values)
            .filter(**self.day_filter, entries__author__is_novice=True, entries__is_draft=False, is_censored=False)
            .annotate(**self.latest, count=Count("entries"))
            .order_by("-latest")
        )

    def search(self, user, search_keys):
        """
        The logic of advanced search feature.
        Notice: Entry counts given in accordance with search filters, it may not
        be the count of ALL entries.
        """

        keywords = search_keys.get("keywords")
        author_nick = search_keys.get("author_nick")
        favorites_only = search_keys.get("is_in_favorites") == "true"
        nice_only = search_keys.get("is_nice_ones") == "true"
        from_date = search_keys.get("from_date")
        to_date = search_keys.get("to_date")
        ordering = search_keys.get("ordering")

        # Input validation
        from_date = parse_date_or_none(from_date, dayfirst=False)
        to_date = parse_date_or_none(to_date, dayfirst=False)

        if ordering not in ("alpha", "newer", "popular"):
            ordering = "newer"

        # Provide a default search term if none present
        if not keywords and not author_nick and not (favorites_only and user.is_authenticated):
            # Translators: This is the default keyword to search when users search with no input.
            keywords = _("common sense")

        filters = {}

        # Filtering
        if favorites_only and user.is_authenticated:
            filters["entries__favorited_by"] = user

        if nice_only:
            filters["entries__vote_rate__gte"] = Decimal("100")

        if author_nick:
            filters["entries__author__username"] = author_nick

        if keywords:
            filters["title__search" if connection.vendor == "postgresql" else "title__icontains"] = keywords

        if from_date:
            filters["entries__date_created__gte"] = from_date

        if to_date:
            filters["entries__date_created__lte"] = to_date

        ordering_map = {"alpha": ["title"], "newer": ["-latest"], "popular": ["-count", "-latest"]}

        qs = (
            Topic.objects.values(*self.values)
            .filter(**self.base_filter, **filters)
            .annotate(count=Count("entries", distinct=True))
        )

        if ordering in ("newer", "popular"):
            qs = qs.alias(**self.latest)

        return qs.order_by(*ordering_map.get(ordering))[: settings.TOPICS_PER_PAGE_DEFAULT]

    def generic_category(self, category):
        return (
            Topic.objects.values(*self.values)
            .filter(**self.base_filter, **self.day_filter, category=category)
            .annotate(**self.latest, count=Count("entries"))
            .order_by("-latest")
        )

    def uncategorized(self):
        return (
            Topic.objects.values(*self.values)
            .filter(**self.base_filter, **self.day_filter)
            .filter(category=None)
            .annotate(**self.latest, count=Count("entries"))
            .order_by("-latest")
        )

    def userstats(self, requester, user, channel, tab):
        if tab == "channels":
            return self.userstats_channels(user, channel)

        handler = UserStatsQueryHandler(user, requester)
        return (
            getattr(handler, tab)()
            .annotate(title=F("topic__title"), slug=F("pk"))
            .order_by(*handler.order_map.get(tab))
            .values(*self.values)
        )

    def userstats_channels(self, user, channel):
        return (
            Topic.objects.values(*self.values)
            .filter(entries__author=user, entries__is_draft=False, category=channel)
            .annotate(latest=Max("entries__date_created"), count=Count("entries"))
            .order_by("-latest")
        )

    def ama(self):
        return (
            Topic.objects.values(*self.values)
            .filter(is_ama=True, is_censored=False)
            .annotate(count=Count("entries__comments"))
            .order_by("-date_created")
        )


class TopicListHandler:
    """
    Handles given topic slug and finds corresponding method in TopicQueryHandler
    to serialize data. Caches topic lists. Handles authentication and validation.
    """

    data = None
    cache_exists = False
    cache_key = None
    cache_set_at = None

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
        :param user: User requesting the list. Used for topics per page and
        checking login requirements/.
        :param slug: Slug of the category.
        :param year: Required for today-in-history.
        :param search_keys: Search keys for "search" (advanced search).
        :param tab: Tab name for tabbed categories.
        :param exclusions: List of category slugs to be excluded in popular.
        None will fallback to DEFAULT_EXCLUSIONS. An empty list [] will include
        all categories.
        :param extra: Any other metadata about the slug.
        """

        if not user.is_authenticated and slug in settings.LOGIN_REQUIRED_CATEGORIES:
            raise PermissionDenied(_("actually, you may benefit from this feature by logging in."))

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
            "generic_category": [self.extra.get("generic_category")],
            "search": [self.user, self.search_keys],
            "popular": [self.exclusions],
            "top": [self.tab],
            "userstats": [self.user, self.extra.get("user_object"), self.extra.get("channel_object"), self.tab],
        }

        # Convert today-in-history => today_in_history
        slug_method = self.slug.replace("-", "_") if self.slug in settings.NON_DB_CATEGORIES else "generic_category"

        # Get the method from TopicQueryHandler.
        try:
            return getattr(self, slug_method)(*arg_map.get(slug_method, []))
        except AttributeError as exc:
            raise NotImplementedError(
                f"Could not find the query method ({slug_method}) for given slug.\n"
                "You need to define a method for non-database"
                f" category '{self.slug}' in 'TopicQueryHandler'"
            ) from exc

    def _validate_exclusions(self, exclusions):
        if self.slug != "popular":
            return ()

        if exclusions is None:
            return settings.DEFAULT_EXCLUSIONS

        return tuple(slug for slug in exclusions if slug in settings.EXCLUDABLE_CATEGORIES)

    def _validate_tab(self, tab):
        if self.slug not in settings.TABBED_CATEGORIES:
            return None

        tab_meta = settings.NON_DB_CATEGORIES_META.get(self.slug)[2]
        available_tabs, default_tab = tab_meta[0].keys(), tab_meta[1]
        return tab if tab in available_tabs else default_tab

    def _validate_year(self, year):
        """Validates and sets the year."""
        if self.slug != "today-in-history":
            return None

        default = settings.YEAR_RANGE[0]

        if year is None:
            return default

        if not isinstance(year, (str, int)):
            raise TypeError("The year either needs to be an integer or a string.")

        if isinstance(year, str):
            year = int(year) if year.isdigit() else default

        return year if year in settings.YEAR_RANGE else default

    def _validate_extra(self, extra):
        return (
            {key: value for key, value in extra.items() if key in self._available_extras and isinstance(value, str)}
            if extra and self.slug in settings.PARAMETRIC_CATEGORIES
            else {}
        )

    def _set_internal_extra(self):
        """
        Set internal extras to change the default behaviour.
        The slug (category) doesn't need to be in parametric categories.
        """

        if self.slug == "userstats":
            # Parse userstats related extras, set the safename of the frame and add hidetabs.
            user_slug = self.extra.get("user")

            if not user_slug:
                raise Http404

            # Converting slug to actual Author object to use it later on in query. (same with the channel)
            user = get_object_or_404(Author, slug=user_slug)
            self.extra["user_object"] = user
            fmtstr = {"username": user.username}

            if self.tab == "channels":
                category_slug = self.extra.get("channel")

                if not category_slug:
                    raise Http404

                channel = get_object_or_404(Category.objects, slug=category_slug)
                self.extra["channel_object"] = channel
                fmtstr["channel"] = channel.name
            else:
                self.extra.pop("channel", None)  # so as not to interfere with cache key

            self.extra["safename"] = settings.NON_DB_CATEGORIES_META["userstats"][2][0][self.tab] % fmtstr
            self.extra["hidetabs"] = "yes"

        elif self.slug not in settings.NON_DB_CATEGORIES:
            self.extra["generic_category"] = get_object_or_404(Category.objects, slug=self.slug)

    @property
    def _caching_allowed(self):
        return not (
            self.slug in settings.UNCACHED_CATEGORIES
            or f"{self.slug}_{self.tab}" in settings.UNCACHED_CATEGORIES
            or settings.DISABLE_CATEGORY_CACHING
        )

    def _cache_data(self, data):
        if self._caching_allowed:
            cache.set(
                self.cache_key,
                {"data": data, "set_at": timezone.now()},
                settings.EXCLUSIVE_TIMEOUTS.get(self.slug, settings.DEFAULT_CACHE_TIMEOUT),
            )
        return data

    def _set_cache_key(self):
        private = f"private_uid_{self.user.id}"
        public = "public"

        scope = private if self.slug in settings.USER_EXCLUSIVE_CATEGORIES else public
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
        self._set_cache_key()
        cached_data = cache.get(self.cache_key)

        if cached_data is None:
            return

        # Cached data detected, check if the day has changed for top or
        # today-in-history (if not, leave cache_exists False to fetch fresh data).
        if self.slug in ("top", "today-in-history"):
            if timezone.localtime(cached_data.get("set_at")).day == timezone.localtime(timezone.now()).day:
                self.cache_exists = True
        else:
            self.cache_exists = True

        if self.cache_exists:
            self._cached_data = cached_data.get("data")
            self.cache_set_at = cached_data.get("set_at")

    def delete_cache(self, flush=False, delimiter=False):
        """
        Deletes cached data. Call this before serialized to get new results.
        :param flush: Set this to True if you don't need new data.
        :param delimiter: Set this to True to limit the time to delete cache.
        """

        if not self.cache_exists:
            return False

        # How many seconds have passed since the last time cache has been set?
        time_elapsed = (timezone.now() - self.cache_set_at).total_seconds()

        if delimiter and time_elapsed < settings.REFRESH_TIMEOUT:
            return False

        cache.delete(self.cache_key)
        self.cache_exists = False

        if flush:
            self.data = ()  # empty tuple

        return True

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
    def refresh_count(self):
        if not (self.cache_exists and self.slug == "today"):
            return 0

        time_elapsed = (timezone.now() - self.cache_set_at).total_seconds()

        if time_elapsed < settings.REFRESH_TIMEOUT:
            # Too soon, check out delete_cache delimiter.
            return 0

        return Entry.objects.filter(date_created__gte=self.cache_set_at).count()


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
            return result.order_by(*self.order_map.get(method.__name__))
        return result

    return wrapped


@for_public_methods(conditional_ordering)
class UserStatsQueryHandler:
    """Queries for user stats on profile page."""

    order_map = {
        "latest": ("-date_created",),
        "favorites": ("-entryfavorites__date_created",),
        "popular": ("-count", "-date_created"),
        "liked": ("-vote_rate", "-date_created"),
        "weeklygoods": ("-vote_rate", "-date_created"),
        "beloved": ("-date_created",),
        "recentlyvoted": ("-last_voted",),
    }

    def __init__(self, user, requester, order=False):
        """
        :param user: An instance of author whose stats to be listed.
        :param requester: An instance of author who request the stats.
        :param order: Set true to get objects ordered (by order_map).
        """

        self.user = user
        self.requester = requester
        self.entries = user.entry_set(manager="objects_published")
        self.order = order

    def latest(self):
        return self.entries.all()

    def favorites(self):
        base = self.user.favorite_entries.filter(author__is_novice=False)

        if self.requester.is_authenticated:
            return base.exclude(author__in=self.requester.blocked.all())

        return base

    def popular(self):
        return self.entries.alias(count=Count("favorited_by")).filter(count__gte=1)

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

        return self.entries.alias(last_voted=Coalesce(Greatest(up, down), up, down)).filter(last_voted__isnull=False)

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
            .alias(frequency=Count("entry"))
            .filter(frequency__gt=1)
            .exclude(Q(pk=self.user.pk) | Q(blocked__in=[self.user.pk]) | Q(pk__in=self.user.blocked.all()))
            .only("username", "slug")
            .order_by("-frequency")[:10]
        )


def entry_prefetch(queryset, user, comments=False):
    """
    Given an entry queryset, optimize it to be shown in templates (entry.html).
    :param queryset: Entry queryset.
    :param user: User who requests the queryset.
    :param comments: Set true to also prefetch comments.
    """
    prefetch = [Prefetch("favorited_by", queryset=Author.objects.only("id"))]

    if comments:
        comments_qs = (
            Comment.objects.annotate(rating=Count("upvoted_by", distinct=True) - Count("downvoted_by", distinct=True))
            .select_related("author")
            .only(
                "id",
                "entry_id",
                "content",
                "date_created",
                "date_edited",
                "author_id",
                "author__slug",
                "author__first_name",
                "author__last_name",
                "author__username",
            )
        )

        if user.is_authenticated:
            vote_states = dict(
                zip(
                    ("is_upvoted", "is_downvoted"),
                    (
                        Exists(model.objects.filter(author=user, comment=OuterRef("pk")))
                        for model in (Comment.upvoted_by.through, Comment.downvoted_by.through)
                    ),
                )
            )
            comments_qs = comments_qs.annotate(**vote_states)

        prefetch.append(Prefetch("comments", queryset=comments_qs))

    base = (
        queryset.select_related("author", "topic")
        .prefetch_related(*prefetch)
        .only(
            "id",
            "content",
            "date_created",
            "date_edited",
            "topic_id",
            "author_id",
            "author__slug",
            "author__username",
            "author__is_private",
            "author__is_novice",
            "topic_id",
            "topic__title",
            "topic__slug",
        )
    )

    if user.is_authenticated:
        vote_states = dict(
            zip(
                ("is_upvoted", "is_downvoted", "is_favorited"),
                (
                    Exists(model.objects.filter(author=user, entry=OuterRef("pk")))
                    for model in (UpvotedEntries, DownvotedEntries, EntryFavorites)
                ),
            )
        )

        return base.annotate(**vote_states)

    return base
