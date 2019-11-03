from .models import Entry, Category, Topic, Author, TopicFollowing
import datetime
from django.shortcuts import get_object_or_404
from functools import wraps
from django.http import HttpResponseBadRequest, Http404
from django.utils import timezone
from decimal import Decimal
from dateutil.parser import parse
from django.urls import reverse_lazy

# time difference of 1 day. if you are going to refactor this, please look for usages beforehand.
time_threshold_24h = timezone.now() - datetime.timedelta(hours=24)
YEAR_RANGE = list(reversed(range(2017, 2020)))  # also set in djdict.js, reversed so as the latest year is on
ENTRIES_PER_PAGE = 10
TOPICS_PER_PAGE = 2  # experimental
ENTRIES_PER_PAGE_PROFILE = 15
nondb_categories = ["bugun", "gundem", "basiboslar", "tarihte-bugun", "kenar", "caylaklar", "takip"]
banned_topics = [  # include banned topics here
    " ", "@", " % ", "seks"]

vote_rates = {"favorite": Decimal(".2"), "increase": Decimal(".2"), "reduce": Decimal("-.2"),
              "anonymous_multiplier": Decimal(".5"), }


def topic_list_qs(request, category_slug, year=None, extend=False):
    """
    Queryset to call on topics that have entires written today.
    category -> Category slug.
    year -> supply for tarihte-bugun
    extend -> full data (for pagination on mobile)

    How pagination works? This function does not paginate. If request contains extended=yes, full content will be
    yielded to paginate in javascript or in view function. If extended is None, then the first page will be the output.
    """
    topic_list = []
    serialized_data = []
    extended = True if request.GET.get("extended") == "yes" or extend else False
    last_entries = None

    if category_slug in nondb_categories:
        if category_slug == "bugun":
            if request.user.is_authenticated:
                last_entries = Entry.objects.filter(date_created__gte=time_threshold_24h).order_by("-date_created")
        elif category_slug == "tarihte-bugun":

            now = datetime.datetime.now()
            last_entries = Entry.objects.filter(date_created__year=year, date_created__day=now.day,
                                                date_created__month=now.month).order_by("-date_created")
        elif category_slug == "basiboslar":
            last_entries = Entry.objects.filter(topic__category=None, date_created__gte=time_threshold_24h).order_by(
                "-date_created")

        elif category_slug == "kenar":
            if request.user.is_authenticated:
                last_entries = Entry.objects_all.filter(author=request.user, is_draft=True).order_by("-date_created")
                serialized_data = []
                for entry in last_entries:
                    serialized_data.append({"title": f"{entry.topic.title}/#{entry.id}",
                                            "slug": reverse_lazy("entry_update", kwargs={"pk": entry.id})})

                serialized_data = serialized_data if extended else serialized_data[:TOPICS_PER_PAGE]
                return serialized_data
            else:
                raise Http404
        elif category_slug == "caylaklar":
            last_entries = Entry.objects_novices.filter(date_created__gte=time_threshold_24h).order_by("-date_created")
        elif category_slug == "takip":
            last_entries = Entry.objects.filter(date_created__gte=time_threshold_24h,
                                                author__in=request.user.following.all()).order_by("-date_created")
            serialized_data = []
            for entry in last_entries:
                serialized_data.append({"title": f"{entry.topic.title}/@{entry.author.username}",
                                        "slug": reverse_lazy("entry_permalink", kwargs={"entry_id": entry.id})})
            return serialized_data

        else:
            raise ZeroDivisionError("Unimplemented yet")
    else:
        category_obj = get_object_or_404(Category, slug=category_slug)
        last_entries = Entry.objects.filter(date_created__gte=time_threshold_24h,
                                            topic__category=category_obj).order_by("-date_created")

    def get_count(topic_obj):
        if category_slug == "tarihte-bugun":
            now_ = datetime.datetime.now()
            return Topic.objects.filter(id=topic_obj.id, entry__date_created__year=year,
                                        entry__date_created__day=now_.day, entry__date_created__month=now_.month,
                                        entry__author__is_novice=False).count()
        if category_slug == "caylaklar":
            return Topic.objects.filter(id=topic_obj.id, entry__date_created__gte=time_threshold_24h,
                                        entry__author__is_novice=True).count()

        return Topic.objects.filter(id=topic_obj.id, entry__date_created__gte=time_threshold_24h,
                                    entry__author__is_novice=False).count()

    if not last_entries:
        return []  # empty respose

    for entry in last_entries:
        if entry.topic not in topic_list:
            topic_list.append(entry.topic)

    for topic in topic_list:
        serialized = {"title": topic.title, "slug": reverse_lazy("topic", kwargs={"slug": topic.slug}),
                      "count": get_count(topic)}
        serialized_data.append(serialized)

    response = serialized_data if extended else serialized_data[:TOPICS_PER_PAGE]
    return response


def categories():
    """
    Provides category list for header.
    """
    return Category.objects.all()


def require_ajax(view):
    @wraps(view)
    def _wrapped_view(request, *args, **kwargs):
        if request.is_ajax():
            return view(request, *args, **kwargs)
        else:
            return HttpResponseBadRequest()

    return _wrapped_view


def get_current_path(request):
    return {'current_path': request.get_full_path()}


def find_after_page(pages_before):
    is_on = pages_before + 1
    page_count = 0
    while is_on > 0:
        page_count += 1
        is_on -= ENTRIES_PER_PAGE
    if is_on == 0:
        page_count += 1
    return page_count


def mark_read(topic, user):
    """
    Marks the topic read, if user is following it.
    """
    try:
        obj = TopicFollowing.objects.get(topic=topic, author=user)
    except TopicFollowing.DoesNotExist:
        return False
    obj.read_at = timezone.now()
    obj.save()
    return True


class NoviceActivityMiddleware:
    """
    https://stackoverflow.com/questions/18434364/django-get-last-user-visit-date/39064596#39064596
    Novice users who visits the website daily should have advantage on novice list, so we need to track last active date
    of novice users, which is what this middleware does. (And also determines novice queue number)
    """
    KEY = "last_activity"

    def __init__(self, get_response):
        self.get_response = get_response  # One-time configuration and initialization.

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_novice and request.user.application_status == "PN":
            last_activity = request.session.get(self.KEY)
            if not last_activity or parse(last_activity) < time_threshold_24h:
                Author.objects.filter(id=request.user.id).update(last_activity=timezone.now())
                request.session[self.KEY] = timezone.now().isoformat()
                # determines the novice queue number on profile page
                queue = Author.objects.filter(is_novice=True, application_status="PN",
                                              last_activity__gte=time_threshold_24h,
                                              application_date__lte=request.user.application_date).count()
                request.session['novice_queue'] = queue
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        return response
