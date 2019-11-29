from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.db.models import Max, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

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

    def __init__(self, user=None, slug=None, extend=False, year=None, fetch_cached=True):
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
        print(59)
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
