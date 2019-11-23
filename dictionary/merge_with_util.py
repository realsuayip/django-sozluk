from .models import Entry, Topic, Category
from django.utils import timezone
import datetime
from django.urls import reverse_lazy
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from django.core.cache import cache

time_threshold_24h = timezone.now() - datetime.timedelta(hours=24)
TOPICS_PER_PAGE = 2  # experimental
nondb_categories = ["bugun", "gundem", "basiboslar", "tarihte-bugun", "kenar", "caylaklar", "takip", "debe"]
login_required_categories = ["bugun", "kenar", "takip"]
do_not_cache = ["kenar"]


class TopicListManager:
    """
    Topic List Manager. views => left_frame for desktop and /basliklar/ for mobile.
    Each non-database category has its own function, note that function names correspond to their slugs, this allows
    us to write a clean code, and each time we have to edit one of them for specific feature it won't be painful.

    If a non-db category has it's own list structure, serialize the data and assign it to self.custom_serialized_data
    current examples include debe, takip, kenar
    """
    entries = None
    custom_serialized_data = None
    cache_exists = False
    valid_cache_key = None
    cache_timeout = 60  # 1 minutes, some categories have their exclusively set

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

        self.extend = extend
        self.slug = slug
        self.year = year
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
        self.entries = Entry.objects.filter(date_created__gte=time_threshold_24h).order_by("-date_created")

    def tarihte_bugun(self):
        now = timezone.now()
        self.entries = Entry.objects.filter(date_created__year=self.year, date_created__day=now.day,
                                            date_created__month=now.month).order_by("-date_created")

    def gundem(self):
        raise ZeroDivisionError("Unimplemented yet")

    def debe(self):
        year, month, day = time_threshold_24h.year, time_threshold_24h.month, time_threshold_24h.day
        entries = Entry.objects.filter(date_created__day=day, date_created__month=month,
                                       date_created__year=year).order_by("-vote_rate")[:TOPICS_PER_PAGE]
        serialized_data = []
        for entry in entries:
            serialized_data.append({"title": f"{entry.topic.title}",
                                    "slug": reverse_lazy("entry_permalink", kwargs={"entry_id": entry.id})})

        self.custom_serialized_data = serialized_data

    def kenar(self):
        if self.user.is_authenticated:
            entries = Entry.objects_all.filter(author=self.user, is_draft=True).order_by("-date_created")
            serialized_data = []
            for entry in entries:
                serialized_data.append({"title": f"{entry.topic.title}/#{entry.id}",
                                        "slug": reverse_lazy("entry_update", kwargs={"pk": entry.id})})

            self.custom_serialized_data = serialized_data

    def takip(self):
        if self.user.is_authenticated:
            entries = Entry.objects.filter(date_created__gte=time_threshold_24h,
                                           author__in=self.user.following.all()).order_by("-date_created")
            serialized_data = []
            for entry in entries:
                serialized_data.append({"title": f"{entry.topic.title}/@{entry.author.username}",
                                        "slug": reverse_lazy("entry_permalink", kwargs={"entry_id": entry.id})})

            self.custom_serialized_data = serialized_data

    def caylaklar(self):
        self.entries = Entry.objects_novices.filter(date_created__gte=time_threshold_24h).order_by("-date_created")

    def generic_category(self):
        category = get_object_or_404(Category, slug=self.slug)
        self.entries = Entry.objects.filter(date_created__gte=time_threshold_24h, topic__category=category).order_by(
            "-date_created")

    def no_category(self):  # başıboşlar
        self.entries = Entry.objects.filter(topic__category=None, date_created__gte=time_threshold_24h).order_by(
            "-date_created")

    def _get_count(self, topic):  # get how many entries are present in the topic
        if self.slug == "tarihte-bugun":
            now = timezone.now()
            return Topic.objects.filter(id=topic.id, entry__date_created__year=self.year,
                                        entry__date_created__day=now.day, entry__date_created__month=now.month,
                                        entry__author__is_novice=False).count()
        elif self.slug == "caylaklar":
            return Topic.objects.filter(id=topic.id, entry__date_created__gte=time_threshold_24h,
                                        entry__author__is_novice=True).count()

        return Topic.objects.filter(id=topic.id, entry__date_created__gte=time_threshold_24h,
                                    entry__author__is_novice=False).count()

    @property
    def serialized(self):
        """
        Serialize Entry queryset data, cache it and return it.
        """
        if self.cache_exists:
            return self.get_cached_data

        if self.custom_serialized_data:
            return self.cache_data(self._delimit_length(self.custom_serialized_data))

        if self.entries:
            topic_list = []
            data = []
            for entry in self.entries:
                if entry.topic not in topic_list:
                    topic_list.append(entry.topic)

            for topic in topic_list:
                data_instance = {"title": topic.title, "slug": reverse_lazy("topic", kwargs={"slug": topic.slug}),
                                 "count": self._get_count(topic)}
                data.append(data_instance)

            return self.cache_data(self._delimit_length(data))

        return []  # found nothing

    def _delimit_length(self, data):
        """
        :param data: Serialized data
        :return: full data if pagination is needed, first page if not.
        """
        delimited = data if self.extend else data[:TOPICS_PER_PAGE]
        return delimited

    def cache_data(self, data):
        if self.slug in do_not_cache:
            return data

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
        cache_key_extended = f"{cache_key}_extended"  # for 'debe' this is obsolete
        cache_key_ultimate = cache_key_extended if self.extend else cache_key
        self.valid_cache_key = cache_key_ultimate
        if cache.get(cache_key_ultimate):
            if self.slug in ["debe", "tarihte-bugun"]:
                if cache.get(cache_key_ultimate).get("set_at_day") == timezone.now().day:
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
