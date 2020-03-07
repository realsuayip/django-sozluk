import base64
from decimal import Decimal

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F, Max, Q, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import Category, Entry, Topic
from ..utils import parse_date_or_none, time_threshold
from ..utils.settings import LOGIN_REQUIRED_CATEGORIES, NON_DB_CATEGORIES, TOPICS_PER_PAGE_DEFAULT, UNCACHED_CATEGORIES


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
    base_annotation = {"latest": Max('entries__date_created')}  # to order_by("-latest")
    base_count = {"count": Count("entries", filter=Q(**day_filter))}

    # Queryset values
    values = ("title", "slug", "count")
    values_entry = values[:2]  # values with count excluded (used for entry listing)

    def bugun(self, user):
        blocked = user.blocked.all()  # To exclude blocked users' topics.
        return Topic.objects.filter(Q(category__in=user.following_categories.all()) | Q(category=None),
                                    **self.base_filter, **self.day_filter).order_by('-latest').annotate(
            **self.base_annotation, **self.base_count).exclude(created_by__in=blocked).values(*self.values)

    def tarihte_bugun(self, year):
        now = timezone.now()
        date_filter = {"entries__date_created__year": year, "entries__date_created__day": now.day,
                       "entries__date_created__month": now.month}

        return Topic.objects.filter(**self.base_filter, **date_filter).order_by('-latest').annotate(
            **self.base_annotation, count=Count("entries", filter=Q(**date_filter))).order_by("-count").values(
            *self.values)

    def gundem(self):
        return [{'title': f'{self.__doc__}', 'slug': 'unimplemented', 'count': 1}]

    def debe(self):
        boundary = time_threshold(hours=24)
        year, month, day = boundary.year, boundary.month, boundary.day
        debe_list = Entry.objects.filter(date_created__day=day, date_created__month=month, date_created__year=year,
                                         topic__is_censored=False).order_by("-vote_rate").annotate(
            title=F("topic__title"), slug=F("pk")).values(*self.values_entry)

        return debe_list[:TOPICS_PER_PAGE_DEFAULT]

    def kenar(self, user):
        return Entry.objects_all.filter(author=user, is_draft=True).order_by("-date_created").annotate(
            title=F('topic__title'), slug=F("pk")).values(*self.values_entry)

    def takip(self, user):
        return Entry.objects.filter(date_created__gte=time_threshold(hours=24),
                                    author__in=user.following.all()).order_by("-date_created").annotate(
            title=Concat(F('topic__title'), Value("/#"), F('author__username')), slug=F("pk")).values(
            *self.values_entry)

    def caylaklar(self):
        caylak_filter = {"entries__author__is_novice": True, "entries__is_draft": False, "is_censored": False}
        return Topic.objects.filter(**self.day_filter, **caylak_filter).order_by('-latest').annotate(
            **self.base_annotation, **self.base_count).values(*self.values)

    def hayvan_ara(self, user, search_keys):
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
        from_date = parse_date_or_none(from_date)
        to_date = parse_date_or_none(to_date)

        if orderding not in ("alpha", "newer", "popular"):
            orderding = "newer"

        # Provide a default search term if none present
        if not keywords and not author_nick and not favorites_only:
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
        return Topic.objects.filter(**self.base_filter, **self.day_filter, category=category).order_by(
            '-latest').annotate(**self.base_annotation, **self.base_count).values(*self.values)

    def basiboslar(self):
        return Topic.objects.filter(**self.base_filter, **self.day_filter, category=None).order_by('-latest').annotate(
            **self.base_annotation, **self.base_count).values(*self.values)


class TopicListHandler:
    """
    Handles given topic slug and finds corresponding method in TopicQueryHandler to serialize data. Caches topic lists.
    Handles authentication, returns general metadata in serialized data such as slug identifier & refresh count.
    """

    cache_timeout = 90  # 1.5 minutes, some categories have their exclusively set
    data = None
    slug_identifier = "/topic/"
    cache_exists = False
    cache_key = None

    def __init__(self, user=None, slug=None, year=None, fetch_cached=True, search_keys=None):
        """
        :param user: only pass request.user, required for topics per page and checking categories with login requirement
        :param slug: slug of the category
        :param year: only required for tarihte-bugun
        :param fetch_cached: set to False if you don't want to fetch cached (refresh button behaviour).
        :param search_keys request.GET for "hayvan-ara" (advanced search).
        """

        self.user = user if user is not None else AnonymousUser

        if not self.user.is_authenticated and slug in LOGIN_REQUIRED_CATEGORIES:
            raise PermissionDenied("User not logged in")

        self.slug = slug
        self.year = year if self.slug == "tarihte-bugun" else None
        self.search_keys = search_keys if self.slug == "hayvan-ara" else {}

        if slug in ("takip", "debe"):
            self.slug_identifier = "/entry/"
        elif slug == "kenar":
            self.slug_identifier = "/entry/update/"

        if self.slug not in UNCACHED_CATEGORIES:
            self._check_cache()

            # user requests new data, so delete the old cached data
            if not fetch_cached and self.cache_exists:
                self.delete_cache()

        if not self.cache_exists:
            # Arguments to be passed for TopicQueryHandler methods. @formatter:off
            arg_map = {
                **dict.fromkeys(("bugun", "kenar", "takip"), [self.user]),
                "tarihte_bugun": [self.year],
                "generic_category": [self.slug],
                "hayvan_ara": [self.user, self.search_keys]
            }  # @formatter:on

            # Convert tarihte-bugun => tarihte_bugun, hayvan-ara => hayvan_ara (for getattr convenience)
            slug_method = self.slug.replace("-", "_") if self.slug in NON_DB_CATEGORIES else "generic_category"

            # Get the method from TopicQueryHandler.
            self.data = getattr(self, slug_method)(*arg_map.get(slug_method, []))

    def _cache_data(self, data):
        if self.slug in UNCACHED_CATEGORIES:
            return data  # Bypass caching

        # Set exclusive timeouts by slug. (default: self.cache_timeout)
        timeouts = {**dict.fromkeys(("debe", "tarihte-bugun"), 86400), "bugun": 300}
        cache.set(self.cache_key, {"data": data, "set_at": timezone.now()}, timeouts.get(self.slug, self.cache_timeout))
        return data

    def _create_cache_key(self):
        cache_type = f"pri_uid_{self.user.id}" if self.slug == "bugun" else "global"
        cache_year = str(self.year) if self.year else ""
        cache_search_suffix = ""

        if self.slug == "hayvan-ara":
            # Create special base64 suffix for search parameters
            available_search_params = (
                "keywords", "author_nick", "is_in_favorites", "is_nice_ones", "from_date", "to_date", "ordering")
            params = {param: self.search_keys.get(param, "_") for param in available_search_params}
            cache_search_suffix = base64.b64encode("".join(params.values()).encode("utf-8")).decode("utf-8")

        self.cache_key = f"{cache_type}_{self.slug}{cache_year}{cache_search_suffix}"

    def _check_cache(self):
        self._create_cache_key()
        cached_data = cache.get(self.cache_key)

        if cached_data is not None:
            if self.slug in ("debe", "tarihte-bugun"):
                # check if the day has changed or not for debe or tarihte-bugun
                if cached_data.get("set_at").day == timezone.now().day:
                    self.cache_exists = True
            else:
                self.cache_exists = True

    def delete_cache(self):
        if self.cache_exists:
            cache.delete(self.cache_key)
            self.cache_exists = False
            self.cache_key = None
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
        # Notice: caching the queryset will evaluate it anyway
        return self._cache_data(tuple(self.data))

    @property
    def refresh_count(self):  # (yenile count)
        if self.cache_exists and self.slug == "bugun":
            set_at = cache.get(self.cache_key).get("set_at")
            if set_at is None:
                return 0
            return Entry.objects.filter(date_created__gte=set_at).count()

        return 0


class TopicListManager(TopicListHandler, TopicQueryHandler):
    """
    Base class for Topic List Management. Whenever a topic list is called, this manager is responsible for it.
    To customize this, do not override this class, instead override each parent class seperately, and create a new
    manager class. This way base classes will always be available.
    """
