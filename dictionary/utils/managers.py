from decimal import Decimal
from datetime import datetime

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.db.models import Max, Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import make_aware

from .settings import time_threshold_24h, TOPICS_PER_PAGE, nondb_categories, login_required_categories, do_not_cache
from ..models import Entry, Topic, Category


class TopicListManager:
    """
    Topic List Manager. views => left_frame for desktop and /basliklar/ for mobile.
    Each non-database category has its own function, note that function names correspond to their slugs, this allows
    us to write a clean code, and each time we have to edit one of them for specific feature it won't be painful.

    If a non-db category has it's own list structure, serialize the data and assign it to self.custom_serialized_data
    current examples include debe, takip, kenar
    """
    data = None
    slug_identifier = "/topic/"
    cache_exists = False
    valid_cache_key = None
    custom_serialized_data = None
    cache_timeout = 90  # 1.5 minutes, some categories have their exclusively set

    def __init__(self, user=None, slug=None, extend=False, year=None, fetch_cached=True, search_keys=None):
        """
        :param user: only pass request.user, required for checking categories with login requirement
        :param slug: slug of the category
        :param extend: if pagination is needed set True, otherwise it will yield the first page, note that no method
        in this class handles pagination. it is either handled in javascript or in view function
        :param year: only required for tarihte-bugun
        :param fetch_cached: set to False if you don't want to fetch cached
        """

        self.user = user if user is not None else AnonymousUser

        if not self.user.is_authenticated and slug in login_required_categories:
            raise PermissionDenied("User not logged in")

        if slug in ["takip", "debe"]:
            self.slug_identifier = "/entry/"
        elif slug == "kenar":
            self.slug_identifier = "/entry/update/"

        self.extend = extend
        self.slug = slug
        self.year = year
        self.search_keys = search_keys

        if self.slug not in do_not_cache:
            self.check_cache()

        if not fetch_cached and self.cache_exists:
            # user requests new data, so delete the old cached data
            self.delete_cache()
            self.cache_exists = False
            self.valid_cache_key = None

        if not self.cache_exists:
            if slug in nondb_categories:
                if slug == "tarihte-bugun":
                    self.tarihte_bugun()
                elif slug == "basiboslar":
                    self.no_category()
                else:
                    getattr(self, slug)()
            else:
                self.generic_category()

    def bugun(self):
        self.data = Topic.objects.filter(entries__date_created__gte=time_threshold_24h).order_by(
            '-last_entry_dt').annotate(last_entry_dt=Max('entries__date_created'), count=Count("entries", filter=Q(
            entries__date_created__gte=time_threshold_24h))).values("title", "slug", "count")

    def tarihte_bugun(self):
        now = timezone.now()
        self.data = Topic.objects.filter(entries__date_created__year=self.year, entries__date_created__day=now.day,
                                         entries__date_created__month=now.month).order_by('-last_entry_dt').annotate(
            last_entry_dt=Max('entries__date_created'),
            count=Count("entries", filter=Q(entries__date_created__gte=time_threshold_24h))).values("title", "slug",
                                                                                                    "count")

    def gundem(self):
        raise ZeroDivisionError("Unimplemented yet")

    def debe(self):
        year, month, day = time_threshold_24h.year, time_threshold_24h.month, time_threshold_24h.day
        entries = Entry.objects.filter(date_created__day=day, date_created__month=month,
                                       date_created__year=year).order_by("-vote_rate")[:TOPICS_PER_PAGE]
        serialized_data = []
        for entry in entries:
            serialized_data.append({"title": f"{entry.topic.title}", "slug": entry.id})

        self.custom_serialized_data = serialized_data

    def kenar(self):
        if self.user.is_authenticated:
            entries = Entry.objects_all.filter(author=self.user, is_draft=True).order_by("-date_created")
            serialized_data = []
            for entry in entries:
                serialized_data.append({"title": f"{entry.topic.title}/#{entry.id}", "slug": entry.id})

            self.custom_serialized_data = serialized_data

    def takip(self):
        if self.user.is_authenticated:
            entries = Entry.objects.filter(date_created__gte=time_threshold_24h,
                                           author__in=self.user.following.all()).order_by("-date_created")
            serialized_data = []
            for entry in entries:
                serialized_data.append({"title": f"{entry.topic.title}/@{entry.author.username}", "slug": entry.id})

            self.custom_serialized_data = serialized_data

    def caylaklar(self):
        self.data = Topic.objects.filter(entries__date_created__gte=time_threshold_24h,
                                         entries__author__is_novice=True).order_by('-last_entry_dt').annotate(
            last_entry_dt=Max('entries__date_created'),
            count=Count("entries", filter=Q(entries__date_created__gte=time_threshold_24h))).values("title", "slug",
                                                                                                    "count")

    def hayvan_ara(self):
        qs = Topic.objects.none()
        keywords = self.search_keys.get("keywords")
        author_nick = self.search_keys.get("author_nick")
        favorites_only = True if self.search_keys.get("is_in_favorites") == "true" else False
        nice_only = True if self.search_keys.get("is_nice_ones") == "true" else False
        from_date = self.search_keys.get("from_date")
        to_date = self.search_keys.get("to_date")
        orderding = self.search_keys.get("ordering")
        # todo input validation
        # todo remove dropdown from mobible (static page)
        # todo implement mobile view

        terminate_search = False

        while not terminate_search:

            if favorites_only and self.user.is_authenticated:
                qs = Topic.objects.filter(entries__favorited_by=self.user).distinct()
                if not qs:
                    break

            if nice_only:
                nice_only_annotate = dict(nice_sum=Sum("entries__vote_rate"))
                nice_only_filter = dict(nice_sum__gte=Decimal("500"))
                if not qs:
                    qs = Topic.objects.annotate(**nice_only_annotate).filter(**nice_only_filter)
                else:
                    qs = qs.annotate(**nice_only_annotate).filter(**nice_only_filter)

                if not qs:
                    break

            if author_nick:
                author_filter = dict(entries__author__username=author_nick)
                if not qs:
                    qs = Topic.objects.filter(**author_filter)
                else:
                    qs = qs.filter(**author_filter)

                if not qs:
                    break

            if keywords:
                keyword_filter = dict(title__icontains=keywords)
                if not qs:
                    qs = Topic.objects.filter(**keyword_filter)
                else:
                    qs = qs.filter(**keyword_filter)

            if from_date:
                date_from = make_aware(datetime.strptime(from_date, "%d.%m.%Y"))
                date_from_filter = dict(date_created__gte=date_from)
                if not qs:
                    qs = Topic.objects.filter(**date_from_filter)
                else:
                    qs = qs.filter(**date_from_filter)

            if to_date:
                date_to = make_aware(datetime.strptime(to_date, "%d.%m.%Y"))
                date_to_filter = dict(date_created__lte=date_to)
                if not qs:
                    qs = Topic.objects.filter(**date_to_filter)
                else:
                    qs = qs.filter(**date_to_filter)

            terminate_search = True

        if qs:
            if orderding == "alpha":
                qs = qs.order_by("title")
            elif orderding == "newer":
                qs = qs.order_by("-date_created")
            elif orderding == "popular":
                qs = qs.annotate(entry_count=Count("entries")).order_by("-entry_count")

        self.custom_serialized_data = qs.annotate(count=Count("entries")).values("title", "slug", "count")

    def generic_category(self):
        category = get_object_or_404(Category, slug=self.slug)
        self.data = Topic.objects.filter(entries__date_created__gte=time_threshold_24h, category=category).order_by(
            '-last_entry_dt').annotate(last_entry_dt=Max('entries__date_created'), count=Count("entries", filter=Q(
            entries__date_created__gte=time_threshold_24h))).values("title", "slug", "count")

    def no_category(self):  #
        self.data = Topic.objects.filter(entries__date_created__gte=time_threshold_24h, category=None).order_by(
            '-last_entry_dt').annotate(last_entry_dt=Max('entries__date_created'), count=Count("entries", filter=Q(
            entries__date_created__gte=time_threshold_24h))).values("title", "slug", "count")

    @property
    def serialized(self):
        """
        Serialize Entry queryset data, cache it and return it.
        """
        if self.cache_exists:
            return self._delimit_length(self.get_cached_data)
        elif self.data:
            return self._delimit_length(self.cache_data(list(self.data)))
        elif self.custom_serialized_data:
            return self._delimit_length(self.cache_data(self.custom_serialized_data))

        return []  # found nothing

    def _delimit_length(self, data):
        """
        :param data: Serialized data
        :return: full data if pagination is needed, first page if not.
        """
        delimited = data if self.extend else data[:TOPICS_PER_PAGE]
        return delimited

    def cache_data(self, data):
        if self.slug == "debe" or self.slug == "tarihte-bugun":
            # these are the same during the day, so caching them longer is reasonable
            set_at_day = timezone.now().day
            cache.set(self.valid_cache_key, {"data": data, "set_at_day": set_at_day}, 86400)  # 24 hours
        elif self.slug == "bugun":
            cache.set(self.valid_cache_key, {"data": data, "set_at": timezone.now()}, 300)  # 5 minutes
        else:
            cache.set(self.valid_cache_key, data, self.cache_timeout)
        return data

    def check_cache(self):
        cache_type = f"pri_uid_{self.user.id}" if self.slug == "bugun" else "global"
        cache_year = str(self.year) if self.year else ""
        cache_key = f"{cache_type}_{self.slug}{cache_year}"
        self.valid_cache_key = cache_key
        if cache.get(cache_key):
            if self.slug in ["debe", "tarihte-bugun"]:
                if cache.get(cache_key).get("set_at_day") == timezone.now().day:
                    self.cache_exists = True
            else:
                self.cache_exists = True

    @property
    def get_cached_data(self):
        if self.slug in ["debe", "tarihte-bugun", "bugun"]:  # exclusively cached
            return cache.get(self.valid_cache_key).get("data")
        return cache.get(self.valid_cache_key)

    def delete_cache(self):
        if self.cache_exists:
            cache.delete(self.valid_cache_key)
            return True
        return False

    @property
    def refresh_count(self):  # (yenile count)
        if self.cache_exists and self.slug == "bugun":
            set_at = cache.get(self.valid_cache_key).get("set_at")
            if set_at is None:
                return 0
            else:
                return Entry.objects.filter(date_created__gte=set_at).count()
        return 0
