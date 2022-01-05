import datetime
import math
import random
import re
import json

from contextlib import suppress
from json.decoder import JSONDecodeError
from urllib.parse import quote, unquote

from django.contrib import messages as notifications
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import connection
from django.db.models import Exists, Max, Min, OuterRef, Prefetch, Q
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _, gettext_lazy
from django.views.generic import ListView, TemplateView

from dateutil.relativedelta import relativedelta
from uuslug import slugify

from dictionary.conf import settings
from dictionary.forms.edit import StandaloneMessageForm
from dictionary.models import (
    Author,
    Category,
    Comment,
    Conversation,
    ConversationArchive,
    Entry,
    Message,
    Topic,
    TopicFollowing,
)
from dictionary.templatetags.filters import IMAGE_REGEX, RE_TOPIC_CHARSET, SEE_EXPR
from dictionary.utils import RE_WEBURL, i18n_lower, proceed_or_404, time_threshold
from dictionary.utils.decorators import cached_context
from dictionary.utils.managers import TopicListManager, entry_prefetch
from dictionary.utils.mixins import IntegratedFormMixin
from dictionary.utils.serializers import LeftFrame
from dictionary.utils.views import SafePaginator
from dictionary.views.edit import EntryCreateMixin


class Index(ListView):
    template_name = "dictionary/index.html"
    context_object_name = "entries"
    extra_context = {"index_type": settings.INDEX_TYPE}

    size = 15
    """
    Number of entries that will show up in homepage.
    """

    page_timeout = 20
    """
    This many seconds need to passed to collect new
    set of random entries.
    """

    nice_bound = 100
    """
    Minimum vote rate an entry needs to have in order to
    show up in homepage. (nice_records)
    """

    nice_cache_timeout = 86400
    """
    Refresh list of nice entries (from which a specified
    number of entries will be randomly selected) after this
    many seconds. (nice_records)
    """

    def get_queryset(self):
        queryset = Entry.objects.filter(pk__in=self.get_pk_set()).order_by()
        return entry_prefetch(queryset, self.request.user)

    @method_decorator(cached_context(timeout=page_timeout, prefix="index_view"))
    def get_pk_set(self):
        records = getattr(self, settings.INDEX_TYPE)()
        return list(records)

    def random_records(self):
        """Author: Peter Be <peterbe.com>"""
        qs = Entry.objects.order_by()

        max_pk = qs.aggregate(Max("pk"))["pk__max"]
        min_pk = qs.aggregate(Min("pk"))["pk__min"]

        if not max_pk or max_pk < self.size * 2:
            return []

        ids = set()

        while len(ids) < self.size:
            next_pk = random.randint(min_pk, max_pk)  # nosec
            while next_pk in ids:
                next_pk = random.randint(min_pk, max_pk)  # nosec

            found = qs.model.objects.filter(pk=next_pk).exists()
            if found:
                ids.add(next_pk)
                yield next_pk

    def nice_records(self):
        nice_pk_set = cached_context(prefix="index_nice_pk_set", timeout=self.nice_cache_timeout)(
            lambda: tuple(Entry.objects.filter(vote_rate__gte=self.nice_bound).values_list("pk", flat=True).order_by())
        )()  # Generated cache key: index_nice_pk_set_context__<lambda>
        return random.sample(nice_pk_set, self.size) if len(nice_pk_set) > self.size else nice_pk_set


class PeopleList(LoginRequiredMixin, ListView):
    template_name = "dictionary/list/people_list.html"
    paginate_by = 15

    tab = None
    tabs = {"following": gettext_lazy("following list"), "blocked": gettext_lazy("blocked list")}

    def get_queryset(self):
        queryset = getattr(self, self.tab)()

        if term := self.request.GET.get("search", "").strip():
            queryset = queryset.filter(username__icontains=term)

        return queryset

    def following(self):
        return self.request.user.following.all()

    def blocked(self):
        return self.request.user.blocked.all()

    def dispatch(self, request, *args, **kwargs):
        tab = kwargs.get("tab")

        if tab is not None and tab not in self.tabs.keys():
            raise Http404

        self.tab = tab or "following"
        self.extra_context = {"tab": self.tab, "title": self.tabs.get(self.tab)}
        return super().dispatch(request, *args, **kwargs)


class ConversationList(LoginRequiredMixin, IntegratedFormMixin, ListView):
    """
    List conversations with a message sending form and a search box.
    Search results handled via GET request in get_queryset.
    """

    model = Conversation
    paginate_by = 10
    template_name = "dictionary/conversation/inbox.html"
    context_object_name = "conversations"
    form_class = StandaloneMessageForm

    def form_valid(self, form):
        try:
            username = form.cleaned_data.get("recipient")
            recipient = Author.objects.get(username=username)
        except Author.DoesNotExist:
            notifications.error(self.request, _("no such person though"))
            return self.form_invalid(form)

        body = form.cleaned_data.get("body")
        sent = Message.objects.compose(self.request.user, recipient, body)

        if not sent:
            notifications.error(self.request, _("we couldn't send your message"))
            return self.form_invalid(form)

        return redirect(reverse("conversation", kwargs={"slug": recipient.slug}))

    def form_invalid(self, form):
        for error in form.non_field_errors() + form.errors.get("body", []):
            notifications.error(self.request, error)

        return super().form_invalid(form)

    def get_queryset(self):
        query_term = i18n_lower(self.request.GET.get("search_term", "")).strip() or None
        return (
            Conversation.objects.list_for_user(self.request.user, query_term)
            .select_related("target")
            .prefetch_related(Prefetch("messages", queryset=Message.objects.select_related("recipient")))
        )


class ConversationArchiveList(ConversationList):
    model = ConversationArchive
    template_name = "dictionary/conversation/inbox_archive.html"

    def get_queryset(self):
        return ConversationArchive.objects.filter(holder=self.request.user).select_related("holder")


class ActivityList(LoginRequiredMixin, ListView):
    template_name = "dictionary/list/activity_list.html"
    context_object_name = "topics"
    paginate_by = 30

    def get_queryset(self):
        return (
            self.request.user.get_following_topics_with_receipt()
            .only("title", "slug")
            .order_by("is_read", "-topicfollowing__read_at")
        )

    def post(self, *args, **kwargs):
        """Bulk read unread topics."""
        TopicFollowing.objects.filter(
            author=self.request.user,
            topic__in=self.request.user.get_following_topics_with_receipt().filter(is_read=False),
        ).update(read_at=timezone.now())

        notifications.info(self.request, _("the topics were mark read"))
        return redirect(self.request.path)

    def dispatch(self, request, *args, **kwargs):
        # Make sure that unread item data is always fresh for this page.
        if request.user.is_authenticated:
            self.request.user.invalidate_unread_topic_count()
        return super().dispatch(request, *args, **kwargs)


class CategoryList(ListView):
    model = Category
    template_name = "dictionary/list/category_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        queryset = self.model.objects.all()
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_followed=Exists(
                    Author.following_categories.through.objects.filter(
                        author=self.request.user, category=OuterRef("pk")
                    )
                )
            )
        return queryset.defer("is_pseudo", "is_default", "weight")


class TopicList(UserPassesTestMixin, TemplateView):
    """Lists topics using LeftFrame interface."""

    template_name = "dictionary/list/topic_list.html"
    cookies = None

    def get_context_data(self, **kwargs):
        params = self.request.GET
        exclusions = self.request.COOKIES.get("lfex")

        if exclusions is not None:
            try:
                parsed = json.loads(unquote(exclusions))
                if isinstance(parsed, list) and all(isinstance(s, str) for s in parsed):
                    exclusions = parsed
                else:
                    raise ValueError
            except (JSONDecodeError, ValueError):
                exclusions = None

        if exclusions is None:
            self.cookies = {"lfex": json.dumps(settings.DEFAULT_EXCLUSIONS)}

        query = (
            self.kwargs.get("slug"),
            self.request.user,
            params.get("year"),
            params,  # search keys
            params.get("tab"),
            exclusions,
            {"user": params.get("user"), "channel": params.get("channel")},  # extras
        )
        manager = TopicListManager(*query)
        frame = LeftFrame(manager, params.get("page"))
        return frame.as_context()

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        if self.cookies:
            for key, val in self.cookies.items():
                response.set_cookie(key, quote(val), samesite="Lax")
        return response

    def test_func(self):
        if self.kwargs.get("slug") in settings.LOGIN_REQUIRED_CATEGORIES and not self.request.user.is_authenticated:
            notifications.info(self.request, _("actually, you may benefit from this feature by logging in."))
            return False
        return True

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        """Resets today's cache (refresh button mobile click event)"""
        if self.kwargs.get("slug") == "today":
            manager = TopicListManager("today", self.request.user)
            manager.delete_cache(flush=True, delimiter=True)
            return redirect(self.request.path)
        return HttpResponseBadRequest()


class TopicEntryList(EntryCreateMixin, IntegratedFormMixin, ListView):
    """
    View to list entries of a topic with an entry creation form.
    View to handle search results of header search box.
    View to handle entry permalinks.
    """
    context_object_name = "entries"
    template_name = "dictionary/list/entry_list.html"
    paginator_class = SafePaginator

    topic = None
    """
    The topic object whose entries to be shown. If url params doesn't match an
    existing topic, a PseudoTopic object will be used to handle creation and
    template rendering.
    """

    entry = None
    """Entry object if the user requests a single entry."""

    view_mode = None
    """
    There are several view modes which filter out entries by specific metadata.
    This determines which queryset will be used to fetch entries. It is caught
    using GET parameters (entry_permalink is handled differently).
    """

    modes = (
        "regular",
        "today",
        "popular",
        "history",
        "nice",
        "nicetoday",
        "search",
        "following",
        "novices",
        "recent",
        "links",
        "acquaintances",
        "answered",
        "images",
    )
    """
    List of filtering modes that are used to filter out entries. User passes
    filtering mode using the query parameter 'a'. For example ?a=today returns
    only today's entries.
    """

    login_required_modes = ("novices", "following", "recent", "acquaintances")
    """These filtering modes require user authentication."""

    redirect = False
    """
    When handling queryset, if there are no new entries found, redirect user
    (if desired) to full topic view.
    """

    def regular(self):
        return self.topic.entries.all()

    def today(self):
        return self.topic.entries.filter(date_created__gte=time_threshold(hours=24))

    def popular(self):
        return self.regular() if self.topic.is_pinned else self.today()

    def history(self):
        year = self.request.GET.get("year", "")

        if not (year.isdigit() and int(year) in settings.YEAR_RANGE):
            self.redirect = True
            return None

        now = timezone.now()
        diff = now.year - int(year)
        delta = timezone.localtime(now - relativedelta(years=diff))
        return self.topic.entries.filter(date_created__date=delta.date())

    def nice(self):
        return self.topic.entries.order_by("-vote_rate")

    def nicetoday(self):
        return self.today().order_by("-vote_rate")

    def search(self):
        """In topic (entry content) search."""
        keywords = self.request.GET.get("keywords", "").strip()

        if not keywords:
            self.redirect = True
            return None

        filters = Q(content__icontains=keywords)

        if keywords.startswith("@") and (username := keywords[1:]):
            with suppress(Author.DoesNotExist):
                author = Author.objects.get(username=username)  # noqa
                filters |= Q(author=author)

        if connection.vendor == "postgresql":
            filters |= Q(content__search=keywords)

        return self.topic.entries.filter(filters)

    def links(self):
        """Shows the entries with links."""
        return self.topic.entries.filter(content__regex=RE_WEBURL)

    def acquaintances(self):
        """Shows the entries of followed users."""
        filters = {"author__in": self.request.user.following.all()}

        # 120 hours defined in TopicQueryHandler's acquaintances_entries
        if self.request.GET.get("recent") is not None:
            filters["date_created__gte"] = time_threshold(hours=120)

        return self.topic.entries.filter(**filters)

    def following(self):
        """User is redirected here from activity_list view."""
        queryset = None
        following = TopicFollowing.objects.filter(author=self.request.user, topic=self.topic).first()

        if following:
            epoch = self.request.GET.get("d")

            try:
                # epoch + 1 because it does not account for the milliseconds
                last_read = timezone.make_aware(datetime.datetime.utcfromtimestamp(int(epoch) + 1), timezone.utc)
            except (ValueError, TypeError, OSError, OverflowError):
                last_read = None

            if last_read and last_read > following.date_created:
                queryset = self._qs_filter(
                    self.topic.entries.filter(date_created__gt=last_read).exclude(Q(author=self.request.user))
                )  # Note: we need to apply _qs_filter because we use queryset results in here.

        if queryset is not None and queryset.exists():
            following.read_at = timezone.now()
            following.save()
            self.request.user.invalidate_unread_topic_count()
            return queryset

        notifications.info(self.request, _("honestly, there was nothing new. so i listed them all."))
        self.redirect = True
        return None

    def novices(self):
        return self.topic.entries.filter(author__is_novice=True, date_created__gte=time_threshold(hours=24))

    def recent(self):
        with suppress(Entry.DoesNotExist):
            latest = self.topic.entries.filter(author=self.request.user).latest("date_created")
            return self.topic.entries.filter(date_created__gte=latest.date_created)
        return None

    def answered(self):
        return self.topic.entries.filter(Exists(Comment.objects.filter(entry=OuterRef("pk"))))

    def images(self):
        return self.topic.entries.filter(content__regex=IMAGE_REGEX)

    def get_queryset(self):
        """Filter queryset by self.view_mode"""
        queryset = None

        if self.entry is not None:
            return entry_prefetch(
                Entry.objects_all.filter(pk=self.entry.pk), self.request.user, comments=self.topic.is_ama
            )

        if self.topic.exists:
            queryset = getattr(self, self.view_mode)()

        if queryset is not None:
            if self.view_mode == "following":
                return queryset  # _qs_filter is applied in the method already

            return self._qs_filter(queryset)

        return self.model.objects.none()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["topic"] = self.topic
        context["mode"] = self.view_mode
        context["entry_permalink"] = self.entry

        if not self.topic.exists:
            return context

        entries = context.get("object_list")
        queryset_size = context.get("paginator").count

        if self.request.user.is_authenticated:
            context["drafts"] = Entry.objects_all.filter(is_draft=True, topic=self.topic, author=self.request.user)

        if queryset_size > 0:
            # Find subsequent and previous entries
            # Get current page's first and last entry, and find the number of entries before and after by date.
            # Using these count data, find what page next entry is located on.
            first_entry = entries[0] if not self.entry else self.entry

            # Redirect to reference?
            if all((self.view_mode == "regular", queryset_size == 1, self.request.GET.get("nr") != "true")) and (
                reference := re.fullmatch(fr"\({SEE_EXPR}: (?!<)({RE_TOPIC_CHARSET})\)", first_entry.content)
            ):
                title = reference.group(1)  # noqa
                with suppress(Topic.DoesNotExist):
                    topic = Topic.objects_published.get(title=title)
                    # Reference needs to have at least 2 entries to hinder mirror references.
                    if topic.entry_count > 1:
                        return {"referrer": self.topic, "referent": topic}

            previous_entries_count, previous_entries_page = 0, 0
            subsequent_entries_count, subsequent_entries_page = 0, 0
            show_subsequent, show_previous = False, False

            # view_mode specific settings
            if self.view_mode in ("popular", "today", "following", "novices"):
                show_previous = True
            elif self.view_mode in (
                "history",
                "entry_permalink",
                "search",
                "nicetoday",
                "recent",
                "links",
                "acquaintances",
                "images",
            ):
                show_previous = True
                show_subsequent = True

            if show_subsequent or show_previous:
                first_entry_date = first_entry.date_created

                previous_entries_count = self._qs_filter(
                    self.topic.entries.filter(date_created__lt=first_entry_date, author__is_novice=False),
                    prefetch=False,
                ).count()

            if show_previous:
                paginate_by = self.get_paginate_by()
                previous_entries_page = math.ceil(previous_entries_count / paginate_by)

            if show_subsequent:
                with suppress(IndexError):
                    last_entry_date = (
                        entries[queryset_size - 1].date_created if not self.entry else self.entry.date_created
                    )

                    subsequent_entries_count = self._qs_filter(
                        self.topic.entries.filter(date_created__gt=last_entry_date, author__is_novice=False),
                        prefetch=False,
                    ).count()

                    if subsequent_entries_count > 0:
                        subsequent_entries_page = self._find_subsequent_page(previous_entries_count)

            context["previous_entries_count"] = previous_entries_count
            context["previous_entries_page"] = previous_entries_page
            context["subsequent_entries_count"] = subsequent_entries_count
            context["subsequent_entries_page"] = subsequent_entries_page
            context["first_entry"] = first_entry

        else:
            # Parameters returned no corresponding entries, show ALL entries count to guide the user
            self.view_mode = "regular"
            context["all_entries_count"] = self._qs_filter(self.regular(), prefetch=False).count()

        return context

    def dispatch(self, request, *args, **kwargs):
        response = self.get_topic()

        # Did get_topic() returned a search result?
        if response and self.request.method != "POST":
            return response

        # Empty request (direct request to /topic/)
        if self.topic is None:
            return redirect(reverse("home"))

        # Regular view. view_mode is used to determine queryset
        if not self.view_mode:
            requested = request.GET.get("a")
            self.view_mode = requested if requested in self.modes else "regular"

        # Check login requirements

        if not request.user.is_authenticated and self.view_mode in self.login_required_modes:
            notifications.info(request, _("actually, you may benefit from this feature by logging in."))
            return redirect(reverse("login"))

        return super().dispatch(request)

    def get_paginate_by(self, *args):
        return (
            self.request.user.entries_per_page
            if self.request.user.is_authenticated
            else settings.ENTRIES_PER_PAGE_DEFAULT
        )

    def render_to_response(self, context, **response_kwargs):
        if (referent := context.get("referent")) is not None:
            referrer = context["referrer"]
            notifications.info(
                self.request,
                _(
                    "you have been redirected by a reference,"
                    " <a href='%(url)s'>click here</a> to return to the original topic."
                )
                % {"url": referrer.get_absolute_url() + "?nr=true"},
                extra_tags="persistent",
            )
            return redirect(referent.get_absolute_url())

        # This redirect is done here because we initially want to get the queryset first to decide if redirect is needed
        return super().render_to_response(context, **response_kwargs) if not self.redirect else self._redirect_to_self()

    def get_topic(self):
        """
        Get topic object (or permalink of an entry) and return it. If no topic
        objects found return a pseudo topic object that could be created via post.
        If unicode_string or query search points to a valid slug (or author or
        entry permalink), redirect to that object.
        """

        # Normal handling of an existing topic
        if self.kwargs.get("slug"):
            self.topic = Topic.objects.get_or_pseudo(slug=self.kwargs.get("slug"))

        # Unicode url parameter handling (e.g. /topic/şıllık redirects to /topic/sillik)
        elif self.kwargs.get("unicode_string"):
            self.topic = Topic.objects.get_or_pseudo(unicode_string=self.kwargs.get("unicode_string"))

            if self.topic.exists:
                return self._redirect_to_self()

        # Entry permalink handling
        elif self.kwargs.get("entry_id"):
            with proceed_or_404(ValueError, OverflowError):
                # Deprecated entry_id for get_or_pseudo.
                klass = (
                    Entry.objects_published
                    if not self.request.user.is_authenticated
                    else Entry.objects_published.exclude(author__in=self.request.user.blocked.all())
                )
                self.entry = get_object_or_404(klass.select_related("topic"), pk=int(self.kwargs.get("entry_id")))
                self.topic = self.entry.topic
                self.view_mode = "entry_permalink"

        # Search handling
        elif self.request.GET.get("q"):
            query = self.request.GET.get("q").strip()

            if not query:
                return False

            if query.startswith("@") and slugify(query):
                author = get_object_or_404(Author, username=query[1:])
                return redirect(author.get_absolute_url())

            if query.startswith("#") and query[1:].isdigit():
                return redirect("entry-permalink", entry_id=query[1:])

            # Set & search for topic
            self.topic = Topic.objects.get_or_pseudo(unicode_string=query)
            if self.topic.exists:
                return self._redirect_to_self()

        # No redirect (normal view)
        return False

    def _redirect_to_self(self):
        # Redirect to topic itself.
        return redirect(self.topic.get_absolute_url())

    def _find_subsequent_page(self, previous_object_count):
        paginate_by = self.get_paginate_by()
        index = previous_object_count + 1

        page = (index // paginate_by) or 1

        if (index % paginate_by == 0) or (index > paginate_by):
            page += 1

        return page

    def _qs_filter(self, queryset, prefetch=True):
        """
        Filter queryset to exclude drafts, blocked users etc. and select and
        prefetch related objects, if required.

        :param queryset: Queryset object of entries.
        :param prefetch: Do you need to prefetch data? If you are going to use
        them, definitely use default value, else set to False to escape
        unnecessary database overhead (e.g. You only need qs to access count).
        :return: Queryset
        """

        novice_view_modes = ["novices", "entry_permalink", "acquaintances"]  # modes in which novice entries are visible

        if self.view_mode == "recent" and self.request.user.is_novice:
            # 'followups' doesn't include novice entries for authors, but does for novices.
            novice_view_modes.append("recent")
        elif self.view_mode == "search" and self.request.GET.get("keywords", "").strip().startswith("@"):
            novice_view_modes.append("search")

        qs = queryset.exclude(is_draft=True)

        if self.view_mode not in novice_view_modes:
            qs = qs.exclude(author__is_novice=True)

        if self.request.user.is_authenticated:
            qs = qs.exclude(author__in=self.request.user.blocked.all())

        if prefetch:
            return entry_prefetch(qs, self.request.user, comments=self.topic.is_ama)

        return qs
