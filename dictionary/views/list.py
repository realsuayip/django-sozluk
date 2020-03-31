import datetime
import math
from contextlib import suppress

from django.contrib import messages as notifications
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import BooleanField, Case, F, Max, Q, When
from django.db.models.query import QuerySet
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import ListView, TemplateView

from dateutil.relativedelta import relativedelta
from uuslug import slugify

from ..forms.edit import EntryForm, StandaloneMessageForm
from ..models import Author, Category, Conversation, Entry, Message, Topic, TopicFollowing
from ..utils import proceed_or_404, time_threshold, turkish_lower
from ..utils.managers import TopicListManager
from ..utils.mixins import IntegratedFormMixin
from ..utils.serializers import LeftFrame
from ..utils.settings import ENTRIES_PER_PAGE_DEFAULT, LOGIN_REQUIRED_CATEGORIES, YEAR_RANGE


def index(request):
    """
    # todo karma skor
    # todo conversation archiving
    """
    return render(request, "dictionary/index.html")


class PeopleList(LoginRequiredMixin, TemplateView):
    template_name = "dictionary/list/people_list.html"


class ConversationList(LoginRequiredMixin, IntegratedFormMixin, ListView):
    """
    List conversations with a message sending form and a search box. Search results
    handled via GET request in get_queryset.
    """

    model = Conversation
    allow_empty = True
    paginate_by = 10
    template_name = "dictionary/conversation/inbox.html"
    context_object_name = "conversations"
    form_class = StandaloneMessageForm

    def form_valid(self, form):
        try:
            username = form.cleaned_data.get("recipient")
            recipient = Author.objects.get(username=username)
        except Author.DoesNotExist:
            notifications.error(self.request, "öyle biri yok")
            return self.form_invalid(form)

        body = form.cleaned_data.get("body")
        sent = Message.objects.compose(self.request.user, recipient, body)
        return redirect(reverse("conversation", kwargs={"slug": recipient.slug})) if sent else self.form_invalid(form)

    def form_invalid(self, form):
        if form.non_field_errors():
            for error in form.non_field_errors():
                notifications.error(self.request, error)

        notifications.error(self.request, "mesajınızı göndermedik")
        return redirect(reverse("messages"))

    def get_queryset(self):
        query_term = turkish_lower(self.request.GET.get("search_term", "")).strip() or None
        return Conversation.objects.list_for_user(self.request.user, query_term)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        unread_messages_count = Message.objects.filter(recipient=self.request.user, read_at__isnull=True).count()
        context["unread_messages_count"] = unread_messages_count
        return context


class ActivityList(LoginRequiredMixin, ListView):
    template_name = "dictionary/list/activity_list.html"
    context_object_name = "topics"
    paginate_by = 30

    def get_queryset(self):
        queryset = self.request.user.following_topics.annotate(
            latest=Max("entries__date_created", filter=~Q(entries__author=self.request.user)),
            read_at=F("topicfollowing__read_at"),
            is_read=Case(When(Q(latest__gt=F("read_at")), then=False), default=True, output_field=BooleanField()),
        ).order_by("is_read", "-topicfollowing__read_at")
        return queryset


class CategoryList(ListView):
    model = Category
    template_name = "dictionary/list/category_list.html"
    context_object_name = "categories"


class TopicList(TemplateView):
    """Lists topics using LeftFrame interface."""

    template_name = "dictionary/list/topic_list.html"

    def get_context_data(self, **kwargs):
        slug = self.kwargs.get("slug")
        year = self.request.GET.get("year")
        page = self.request.GET.get("page")
        tab = self.request.GET.get("tab")
        search_keys = self.request.GET

        manager = TopicListManager(self.request.user, slug, year, search_keys, tab)
        frame = LeftFrame(manager, page)
        return frame.as_context()

    def dispatch(self, request, *args, **kwargs):
        """User tries to view unauthorized category."""
        if self.kwargs.get("slug") in LOGIN_REQUIRED_CATEGORIES and not request.user.is_authenticated:
            notifications.info(request, "aslında giriş yaparsan bu özellikten yararlanabilirsin.")
            return redirect(reverse("login"))

        return super().dispatch(request)

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        """Resets bugun's cache (refresh button mobile click event)"""
        if self.kwargs.get("slug") == "bugun":
            manager = TopicListManager(self.request.user, "bugun")
            manager.delete_cache(flush=True)
            return redirect(self.request.path)
        return HttpResponseBadRequest()


class TopicEntryList(IntegratedFormMixin, ListView):
    """
    View to list entries of a topic with an entry creation form.
    View to handle search results of header search box. (başlık, #entry ya da @yazar)
    View to handle entry permalinks.
    """

    model = Entry
    form_class = EntryForm
    context_object_name = "entries"
    template_name = "dictionary/list/entry_list.html"

    topic = None
    """The topic object whose entries to be shown. If url doesn't match an existing topic,
       a PseudoTopic object created via TopicManager will be used to handle creation & template rendering."""

    view_mode = None
    """There are several view modes which filter out entries by specific metadata. This determines which queryset will
       be used to fetch entries. It is caught using GET parameters."""

    entry_permalink = False
    """This will be set to (entry_id) if user requests a single entry. It's similar to view_mode, but it needs some
       other metadata and seperated from view_mode as they use different urls."""

    redirect = False
    """When handling following topics, if there are no new entries found, redirect user to full topic view."""

    def form_valid(self, form):
        """
        User sent new entry, whose topic may or may not be existant. If topic exists, adds the entry and redirects to
        the entry permalink. If topic doesn't exist, topic is created if the title is valid. Entry.save() automatically
        sets created_by field of the topic.
        """

        # Hinders sending entries to banned topics.
        if self.topic.exists and self.topic.is_banned:  # Cannot check is_banned before chechking its existance
            # not likely to occur in normal circumstances so you may include some humor here.
            notifications.error(self.request, "olmaz ki canım... hürrüpü")
            return self.form_invalid(form)

        # Entry creation handling
        entry = form.save(commit=False)
        entry.author = self.request.user
        is_draft = form.cleaned_data.get("is_draft")  # for redirect purposes

        # Hinders entry publishing for suspended users.
        if self.request.user.is_suspended:
            is_draft = True  # for redirect purposes
            entry.is_draft = True

        if self.topic.exists:
            entry.topic = self.topic
        else:
            # Create topic
            try:
                # make sure that there is no topic with empty slug, empty slug is reserved for validity testing
                if not slugify(self.topic.title):
                    notifications.error(self.request, "öyle başlık mı olur hıyarağası.")
                    return self.form_invalid(form)

                Topic(title=self.topic.title).full_clean()
            except ValidationError as error:
                for msg in error.messages:
                    notifications.error(self.request, msg)
                return self.form_invalid(form)

            entry.topic = Topic.objects.create_topic(title=self.topic.title)

        entry.save()

        if is_draft:
            notifications.info(self.request, "kenara attık onu")
            return redirect(reverse("entry_update", kwargs={"pk": entry.pk}))

        notifications.info(self.request, "entry başarıyla statosfere yollandı")
        return redirect(reverse("entry-permalink", kwargs={"entry_id": entry.id}))

    def form_invalid(self, form):
        """
        This can be called by invalid Topic title or banned topic post. Because no queryset is returned, a custom
        form_invalid method is necessary. In this method, appropriate redirections are made to ensure that user finds
        themselves where they started. Error messages supplied via notifications in form_valid exception catch.
        """

        if form.errors:
            for err in form.errors["content"]:
                notifications.error(self.request, err)

        unicode_url_argument = None

        if self.kwargs.get("unicode_string"):
            unicode_url_argument = self.kwargs.get("unicode_string")
        elif self.request.GET.get("q"):
            unicode_url_argument = self.request.GET.get("q")

        if unicode_url_argument:
            return redirect(reverse("topic-unicode-url", kwargs={"unicode_string": unicode_url_argument}))

        if self.kwargs.get("entry_id"):
            return redirect(reverse("entry-permalink", kwargs={"entry_id": self.kwargs.get("entry_id")}))

        return redirect(reverse("topic", kwargs={"slug": self.kwargs.get("slug")}))

    def today(self):
        return self.topic.entries.filter(date_created__gte=time_threshold(hours=24))

    def today_in_history(self):
        year = self.request.GET.get("year")

        with suppress(ValueError, OverflowError):
            if int(year) in YEAR_RANGE:
                now = timezone.now()
                diff = now.year - int(year)
                delta = now - relativedelta(years=diff)
                return self.topic.entries.filter(date_created__date=delta.date())

        return self.model.objects.none()

    def nice(self):
        return self.topic.entries.order_by("-vote_rate")

    def nicetoday(self):
        return self.today().order_by("-vote_rate")

    def search(self):
        """In topic (entry content) search."""
        keywords = self.request.GET.get("keywords")

        if keywords:
            if keywords.startswith("@"):
                with suppress(Author.DoesNotExist):
                    author = Author.objects.get(username=keywords[1:])
                    return self.topic.entries.filter(author=author)
            else:
                # use postgresql to make searches more advanced if desired
                return self.topic.entries.filter(content__icontains=keywords)

        return self.model.objects.none()

    def following(self):
        """User is redirected here from (olay) link in header (view -> activity_list)"""
        queryset = None

        if self.request.user.is_authenticated:
            following = TopicFollowing.objects.filter(author=self.request.user, topic=self.topic).first()

            if following:
                date = self.request.GET.get("d")

                try:
                    last_read = timezone.make_aware(datetime.datetime.fromtimestamp(int(date)))
                except (ValueError, TypeError, OSError):
                    last_read = None

                if last_read:
                    queryset = self.topic.entries.filter(date_created__gt=last_read).exclude(author=self.request.user)

            if queryset is not None and queryset.exists():
                following.read_at = timezone.now()
                following.save()
                notifications.info(self.request, f"{queryset.count()} tane entry")
                return queryset

        notifications.info(self.request, "pek bişey bulamadım açıkçası, buyrun hepsi")
        self.redirect = True
        return self.model.objects.none()

    def caylaklar(self):
        return self.topic.entries.filter(author__is_novice=True, date_created__gte=time_threshold(hours=24))

    def get_queryset(self):
        """Filter queryset by self.view_mode"""
        queryset = None
        filtering_modes = ("today", "today_in_history", "nice", "nicetoday", "search", "following", "caylaklar")

        if self.entry_permalink:
            queryset = self.topic.entries.filter(pk=self.entry_permalink)

        elif self.topic.exists:
            if self.view_mode in filtering_modes:
                queryset = getattr(self, self.view_mode)()
            else:
                # view mode is regular
                queryset = self.topic.entries.all()

        if queryset is not None:
            return self._qs_filter(queryset)

        return self.model.objects.none()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["topic"] = self.topic
        context["mode"] = self.view_mode
        context["entry_permalink"] = bool(self.entry_permalink)

        if not self.topic.exists:
            return context

        entries = context.get("object_list")

        if isinstance(entries, QuerySet):
            queryset_size = entries.count()
        else:
            queryset_size = len(entries)

        if queryset_size > 0:
            # Find subsequent and previous entries
            # Get current page's first and last entry, and find the number of entries before and after by date.
            # Using these count data, find what page next entry is located on.

            previous_entries_count, previous_entries_page = 0, 0
            subsequent_entries_count, subsequent_entries_page = 0, 0
            show_subsequent, show_previous = False, False

            # view_mode specific settings
            if self.view_mode in ("today", "following", "caylaklar"):
                show_previous = True
            elif self.view_mode in ("today_in_history", "entry_permalink", "search", "nicetoday"):
                show_previous = True
                show_subsequent = True

            if show_subsequent or show_previous:
                first_entry_date = entries[0].date_created

                previous_entries_count = self._qs_filter(
                    self.topic.entries.filter(date_created__lt=first_entry_date, author__is_novice=False),
                    prefecth=False,
                ).count()

            if show_previous:
                paginate_by = self.get_paginate_by()
                previous_entries_page = math.ceil(previous_entries_count / paginate_by)

            if show_subsequent:
                with suppress(IndexError):
                    last_entry_date = entries[queryset_size - 1].date_created

                    subsequent_entries_count = self._qs_filter(
                        self.topic.entries.filter(date_created__gt=last_entry_date, author__is_novice=False),
                        prefecth=False,
                    ).count()

                    if subsequent_entries_count > 0:
                        subsequent_entries_page = self._find_subsequent_page(previous_entries_count)

            context["previous_entries_count"] = previous_entries_count
            context["previous_entries_page"] = previous_entries_page
            context["subsequent_entries_count"] = subsequent_entries_count
            context["subsequent_entries_page"] = subsequent_entries_page

        else:
            # Parameters returned no corresponding entries, show ALL entries count to guide the user
            if self.view_mode in ("today", "today_in_history", "nice", "nicetoday", "search", "caylaklar", "following"):
                context["all_entries_count"] = self._qs_filter(self.topic.entries.all(), prefecth=False).count()

        return context

    def dispatch(self, request, *args, **kwargs):
        search_redirect = self.get_topic()

        # Did get_topic() returned a search result?
        if search_redirect:
            return search_redirect

        # Empty request (direct request to /topic/)
        if self.topic is None:
            return redirect(reverse("home"))

        # Regular view. view_mode is used to determine queryset
        if not self.view_mode:
            if request.GET.get("day") == "today":
                self.view_mode = "today"
            elif request.GET.get("year"):
                self.view_mode = "today_in_history"
            elif request.GET.get("a"):
                self.view_mode = request.GET.get("a")
            else:
                self.view_mode = "regular"

        # Check login requirements

        login_required_modes = ("caylaklar", "following")
        if not request.user.is_authenticated and self.view_mode in login_required_modes:
            notifications.info(request, "aslında giriş yaparsan bu özellikten yararlanabilirsin.")
            return redirect(reverse("login"))

        return super().dispatch(request)

    def get_paginate_by(self, *args):
        if self.request.user.is_authenticated:
            return self.request.user.entries_per_page
        return ENTRIES_PER_PAGE_DEFAULT

    def render_to_response(self, context, **response_kwargs):
        # can only be caused by self.following()
        # this redirect is done here because we initially want to get the queryset first to decide if redirect is needed
        return super().render_to_response(context, **response_kwargs) if not self.redirect else self._redirect_to_self()

    def get_topic(self):
        """
        Get topic object (or permalink of an entry) and return it. If no topic objects found return a pseudo topic
        object that could be created via post. If unicode_string or query search points to a valid slug
        (or author or entry permalink), redirect to that object.
        """
        #  Normal handling of an existing topic
        if self.kwargs.get("slug"):
            self.topic = Topic.objects.get_or_pseudo(slug=self.kwargs.get("slug").strip())

        #  Unicode url parameter handling (e.g. /topic/şıllık redirects to /topic/sillik)
        elif self.kwargs.get("unicode_string"):
            self.topic = Topic.objects.get_or_pseudo(unicode_string=self.kwargs.get("unicode_string").strip())

            if self.topic.exists:
                return self._redirect_to_self()

        #  Entry permalink handling
        elif self.kwargs.get("entry_id"):
            with proceed_or_404(ValueError, OverflowError):
                entry_id = int(self.kwargs.get("entry_id"))
                self.topic = Topic.objects.get_or_pseudo(entry_id=entry_id)

                if self.request.user.is_authenticated:
                    entry = self.topic.entries.get(pk=entry_id)

                    if entry.author in self.request.user.blocked.all():
                        raise Http404

                self.entry_permalink = entry_id
                self.view_mode = "entry_permalink"

        #  Search handling
        elif self.request.GET.get("q"):
            query = self.request.GET.get("q").strip()

            if not query:
                return False

            if query.startswith("@") and slugify(query):
                return redirect("user-profile", slug=slugify(query[1:]))

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

    def _find_subsequent_page(self, pages_before):
        is_on = pages_before + 1
        page_count = 0
        while is_on > 0:
            page_count += 1
            is_on -= self.get_paginate_by()
        if is_on == 0:
            page_count += 1
        return page_count

    def _qs_filter(self, queryset, prefecth=True):
        """
        Filter queryset to exclude drafts, blocked users etc. and select and prefetch related objects, if required.

        :param queryset: Queryset object of entries.
        :param prefecth: Do you need to prefecth data? If you are going to use them, definitely use default value, else
        set to False to escape unnecessary database overhead (e.g. You only need qs to access count).
        :return: qs
        """

        qs = queryset.exclude(is_draft=True)

        if self.view_mode not in ["caylaklar", "entry_permalink"]:
            qs = qs.exclude(author__is_novice=True)

        if self.request.user.is_authenticated:
            qs = qs.exclude(author__in=self.request.user.blocked.all())

        return qs.select_related("author", "topic").prefetch_related("favorited_by") if prefecth else qs
