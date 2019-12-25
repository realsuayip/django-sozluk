from decimal import Decimal
from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.db.models import Max, Count, Sum, Q, F, Value
from django.db.models.functions import Concat
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import make_aware

from dateutil.parser import parse

from ..models import Entry, Topic, Category
from ..models.managers.topic import TopicManager
from ..utils.settings import (TIME_THRESHOLD_24H, TOPICS_PER_PAGE_DEFAULT, NON_DB_CATEGORIES, LOGIN_REQUIRED_CATEGORIES,
                              UNCACHED_CATEGORIES)


class TopicListManager:
    """
    Topic List Manager. views => left_frame for desktop and /basliklar/ for mobile.
    Each non-database category has its own function, note that function names correspond to their slugs, this allows
    us to write a clean code, and each time we have to edit one of them for specific feature it won't be painful.
    """
    # constants
    cache_timeout = 90  # 1.5 minutes, some categories have their exclusively set

    # manager related stuff
    data = None
    slug_identifier = "/topic/"
    cache_exists = False
    cache_key = None

    # queryset filters
    day_filter = dict(entries__date_created__gte=TIME_THRESHOLD_24H)
    base_filter = dict(entries__is_draft=False, entries__author__is_novice=False)

    # queryset annotations
    base_annotation = dict(latest=Max('entries__date_created'))  # for order_by("-latest")
    base_count = dict(count=Count("entries", filter=Q(**day_filter)))

    # queryset values
    values = ["title", "slug", "count"]
    values_entry = values[:2]  # values with count excluded (used for entry listing)

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

        if self.user.is_authenticated:
            blocked = self.user.blocked.all()
            self.auth_exclude_filter = dict(created_by__in=blocked)  # use ONLY with LOGIN_REQUIRED_CATEGORIES

        if slug in ["takip", "debe"]:
            self.slug_identifier = "/entry/"
        elif slug == "kenar":
            self.slug_identifier = "/entry/update/"

        self.slug = slug
        self.year = year
        self.search_keys = search_keys

        if self.slug not in UNCACHED_CATEGORIES:
            self.check_cache()

            if not fetch_cached and self.cache_exists:
                # user requests new data, so delete the old cached data
                self.delete_cache()
                self.cache_exists = False
                self.cache_key = None

        if not self.cache_exists:
            if slug in NON_DB_CATEGORIES:
                # convert tarihte-bugun => tarihte_bugun, hayvan-ara => hayvan_ara (for getattr convenience)
                slug = slug.replace("-", "_")
                getattr(self, slug)()
            else:
                self.generic_category()

    def bugun(self):
        self.data = Topic.objects.filter(Q(category__in=self.user.following_categories.all()) | Q(category=None),
                                         **self.base_filter, **self.day_filter, ).order_by('-latest').annotate(
            **self.base_annotation, **self.base_count).exclude(**self.auth_exclude_filter).values(*self.values)

    def tarihte_bugun(self):
        now = timezone.now()
        date_filter = dict(entries__date_created__year=self.year, entries__date_created__day=now.day,
                           entries__date_created__month=now.month)

        self.data = Topic.objects.filter(**self.base_filter, **date_filter).order_by('-latest').annotate(
            **self.base_annotation, count=Count("entries", filter=Q(**date_filter))).order_by("-count").values(
            *self.values)

    def gundem(self):
        raise ZeroDivisionError("Unimplemented yet", self.slug)

    def debe(self):
        year, month, day = TIME_THRESHOLD_24H.year, TIME_THRESHOLD_24H.month, TIME_THRESHOLD_24H.day
        debe_list = Entry.objects.filter(date_created__day=day, date_created__month=month,
                                         date_created__year=year).order_by("-vote_rate").annotate(
            title=F("topic__title"), slug=F("pk")).values(*self.values_entry)

        self.data = debe_list[:TOPICS_PER_PAGE_DEFAULT]

    def kenar(self):
        if self.user.is_authenticated:
            self.data = Entry.objects_all.filter(author=self.user, is_draft=True).order_by("-date_created").annotate(
                title=F('topic__title'), slug=F("pk")).values(*self.values_entry)

    def takip(self):
        if self.user.is_authenticated:
            self.data = Entry.objects.filter(date_created__gte=TIME_THRESHOLD_24H,
                                             author__in=self.user.following.all()).order_by("-date_created").annotate(
                title=Concat(F('topic__title'), Value("/#"), F('author__username')), slug=F("pk")).values(
                *self.values_entry)

    def caylaklar(self):
        caylak_filter = dict(entries__author__is_novice=True, entries__is_draft=False)
        self.data = Topic.objects.filter(**self.day_filter, **caylak_filter).order_by('-latest').annotate(
            **self.base_annotation, **self.base_count).values(*self.values)

    def hayvan_ara(self):
        qs = Topic.objects
        keywords = self.search_keys.get("keywords")
        author_nick = self.search_keys.get("author_nick")
        favorites_only = self.search_keys.get("is_in_favorites") == "true"
        nice_only = self.search_keys.get("is_nice_ones") == "true"
        from_date = self.search_keys.get("from_date")
        to_date = self.search_keys.get("to_date")
        orderding = self.search_keys.get("ordering")

        # Input validation

        if from_date:
            try:
                parse(from_date)
            except ValueError:
                from_date = None

        if to_date:
            try:
                parse(to_date)
            except ValueError:
                to_date = None

        if orderding not in ("alpha", "newer", "popular"):
            orderding = "newer"

        if not keywords and not author_nick and not favorites_only:
            keywords = "akıl fikir"

        count_filter = dict(count=Count("entries", distinct=True))

        if favorites_only and self.user.is_authenticated:
            qs = qs.filter(entries__favorited_by=self.user)

        if nice_only:
            qs = qs.annotate(nice_sum=Sum("entries__vote_rate")).filter(nice_sum__gte=Decimal("500"))

        if author_nick:
            qs = qs.filter(entries__author__username=author_nick)

        if keywords:
            qs = qs.filter(title__icontains=keywords)

        if from_date:
            date_from = make_aware(datetime.strptime(from_date, "%d.%m.%Y"))
            qs = qs.filter(date_created__gte=date_from)

        if to_date:
            date_to = make_aware(datetime.strptime(to_date, "%d.%m.%Y"))
            qs = qs.filter(date_created__lte=date_to)

        if qs and not isinstance(qs, TopicManager):
            qs = qs.filter(**self.base_filter).annotate(**count_filter)
            if orderding == "alpha":
                qs = qs.order_by("title")
            elif orderding == "newer":
                qs = qs.order_by("-date_created")
            elif orderding == "popular":
                qs = qs.order_by("-count", "-date_created")

            result = qs.values(*self.values)
            self.data = result[:TOPICS_PER_PAGE_DEFAULT]
        else:
            self.data = qs.none()  # nothing found

    def generic_category(self):
        category = get_object_or_404(Category, slug=self.slug)
        self.data = Topic.objects.filter(**self.base_filter, **self.day_filter, category=category).order_by(
            '-latest').annotate(**self.base_annotation, **self.base_count).values(*self.values)

    def basiboslar(self):  # No category supplied.
        self.data = Topic.objects.filter(**self.base_filter, **self.day_filter, category=None).order_by(
            '-latest').annotate(**self.base_annotation, **self.base_count).values(*self.values)

    def cache_data(self, data):
        if self.slug in UNCACHED_CATEGORIES:
            # bypass caching
            return data

        if self.slug == "debe" or self.slug == "tarihte-bugun":
            # these are the same during the day, so caching them longer is more reasonable
            set_at_day = timezone.now().day
            cache.set(self.cache_key, {"data": data, "set_at_day": set_at_day}, 86400)  # 24 hours
        elif self.slug == "bugun":
            cache.set(self.cache_key, {"data": data, "set_at": timezone.now()}, 300)  # 5 minutes
        else:
            cache.set(self.cache_key, data, self.cache_timeout)
        return data

    def check_cache(self):
        cache_type = f"pri_uid_{self.user.id}" if self.slug == "bugun" else "global"
        cache_year = str(self.year) if self.year else ""
        key = f"{cache_type}_{self.slug}{cache_year}"
        self.cache_key = key
        if cache.get(key):
            if self.slug in ["debe", "tarihte-bugun"]:
                # check if the day has changed or not for debe or tarihte-bugun
                if cache.get(key).get("set_at_day") == timezone.now().day:
                    self.cache_exists = True
            else:
                self.cache_exists = True

    def delete_cache(self):
        if self.cache_exists:
            cache.delete(self.cache_key)
            return True
        return False

    @property
    def serialized(self):
        # serialize topic queryset data, cache it and return it.
        if self.cache_exists:
            return self.get_cached_data

        return self.cache_data(list(self.data))

    @property
    def get_cached_data(self):
        if self.slug in ["debe", "tarihte-bugun", "bugun"]:  # exclusively cached
            return cache.get(self.cache_key).get("data")
        return cache.get(self.cache_key)

    @property
    def refresh_count(self):  # (yenile count)
        if self.cache_exists and self.slug == "bugun":
            set_at = cache.get(self.cache_key).get("set_at")
            if set_at is None:
                return 0
            return Entry.objects.filter(date_created__gte=set_at).count()

        return 0
