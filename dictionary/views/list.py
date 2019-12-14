import datetime
import math
import random

from django.contrib import messages as notifications
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, F, Max, Case, When, IntegerField
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import FormMixin
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator

from ..forms.edit import EntryForm
from ..models import Author, Entry, Topic, Category, Conversation, TopicFollowing, Message
from ..utils.managers import TopicListManager
from ..utils.settings import TOPICS_PER_PAGE_DEFAULT, YEAR_RANGE, ENTRIES_PER_PAGE_DEFAULT, NON_DB_CATEGORIES, \
    TIME_THRESHOLD_24H, BANNED_TOPICS, NON_DB_SLUGS_SAFENAMES


def index(request):
    # todo flatpages for about us etc.
    # todo scrollbar tracking
    # todo karma skor
    # todo hayvan ara
    # todo: başlık yönlendirme (türkçe düzeltme gibi)
    return render(request, "dictionary/index.html")


class PeopleList(LoginRequiredMixin, TemplateView):
    template_name = "dictionary/list/people_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blocked'] = self.request.user.blocked
        context['following'] = self.request.user.following
        return context


class ConversationList(LoginRequiredMixin, ListView):
    model = Conversation
    allow_empty = True
    paginate_by = 3
    template_name = "dictionary/conversation/inbox.html"
    context_object_name = "conversations"

    def get_queryset(self):
        return Conversation.objects.list_for_user(self.request.user)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        unread_messages_count = Message.objects.filter(recipient=self.request.user, read_at__isnull=True).count()
        context["unread_messages_count"] = unread_messages_count
        return context


class ActivityList(LoginRequiredMixin, ListView):
    model = TopicFollowing
    template_name = "dictionary/list/activity_list.html"
    context_object_name = "topics_following"
    paginate_by = 30

    def get_queryset(self):
        return TopicFollowing.objects.filter(author=self.request.user).annotate(
            latest=Max("topic__entries__date_created"),
            is_read=Case(When(Q(latest__gt=F("read_at")), then=1), When(Q(latest__lt=F("read_at")), then=2),
                         output_field=IntegerField()), ).order_by("is_read", "-read_at")


class CategoryList(ListView):
    model = Category
    template_name = "dictionary/list/category_list.html"
    context_object_name = "categories"


class TopicList(ListView):
    """
        Topic list (başlıklar) for mobile views such as "bugün", "gündem",
        Desktop equivalent => views.json.TopicListAsync

        cache_key for bugun-> bugun_extended_{self.request.user.id} (also used in _category)
        refresh_count -> for bugun only, "yenile" button count
    """
    model = Topic
    context_object_name = "topics"
    template_name = "dictionary/list/topic_list.html"
    refresh_count = 0
    slug_identifier = None

    def get_queryset(self):
        year = None
        slug = self.kwargs['slug']

        if slug == "tarihte-bugun":
            request_year = self.request.GET.get("year")
            session_year = self.request.session.get("year")
            random_year = random.choice(YEAR_RANGE)

            if request_year:
                try:
                    if int(request_year) not in YEAR_RANGE:
                        if session_year:
                            year = session_year
                    else:
                        year = request_year
                except (ValueError, OverflowError):
                    if session_year:
                        year = session_year
                    else:
                        year = random_year
            elif session_year:
                year = session_year
            else:
                year = random_year

            self.request.session["year"] = year

        if slug == "bugun" and not self.request.user.is_authenticated:
            return self.model.objects.none()

        if slug == "hayvan-ara":
            raise ZeroDivisionError("Unimplemented yet")

        manager = TopicListManager(self.request.user, slug, year=year)
        self.refresh_count = manager.refresh_count
        self.slug_identifier = manager.slug_identifier
        return manager.serialized

    def get_context_data(self, **kwargs):
        slug = self.kwargs['slug']

        if slug in NON_DB_CATEGORIES:
            title = NON_DB_SLUGS_SAFENAMES[slug]
        else:
            title = Category.objects.get(slug=slug).name

        context = super().get_context_data(**kwargs)
        context['page_safename'] = title
        if self.request.session.get("year"):
            context["current_year"] = self.request.session.get("year")
        context['slug_name'] = slug
        if slug == "tarihte-bugun":
            context["year_range"] = YEAR_RANGE

        context['refresh_count'] = self.refresh_count
        context['slug_identifier'] = self.slug_identifier
        return context

    def get_paginate_by(self, queryset):
        if self.request.user.is_authenticated:
            return self.request.user.topics_per_page
        return TOPICS_PER_PAGE_DEFAULT

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        if self.kwargs['slug'] == "bugun":
            # reset cache (refresh button mobile click event)
            manager = TopicListManager(self.request.user, "bugun")
            manager.delete_cache()
            return redirect(self.request.path)
        return HttpResponseBadRequest()


class TopicEntryList(ListView, FormMixin):
    model = Entry
    form_class = EntryForm
    context_object_name = "entries"
    template_name = "dictionary/list/entry_list.html"

    topic = None
    view_mode = None
    entry_permalink = False
    redirect = False

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        if self.topic.title in BANNED_TOPICS:
            # not likely to occur in normal circumstances so you may include some humor here.
            notifications.error(self.request, "olmaz ki canım... hürrüpü")
            return self.form_invalid(form)
        # Entry creation handling
        entry = form.save(commit=False)
        entry.author = self.request.user
        is_draft = form.cleaned_data.get("is_draft")

        if self.topic.exists:
            entry.topic = self.topic
        else:
            # Create topic
            try:
                # make sure that there is no topic with empty slug, empty slug is reserved for validity testing
                Topic(title=self.topic.title).full_clean()
            except ValidationError as error:
                for msg in error.messages:
                    notifications.error(self.request, msg)
                return self.form_invalid(form)

            entry.topic = Topic.objects.create_topic(title=self.topic.title)

        entry.save()

        if is_draft:
            notifications.info(self.request, "kenara attık onu")
            if self.topic.exists:
                return self._redirect_to_self()
            else:
                return redirect(reverse("entry_update", kwargs={"pk": entry.pk}))

        return redirect(reverse("entry-permalink", kwargs={"entry_id": entry.id}))

    def form_invalid(self, form):
        """
        This can be called by invalid Topic title or banned topic post. Because no queryset is returned, a custom
        form_invalid method is necessary. In this method, appropriate redirections are made to ensure that user finds
        themselves where they started. Error messages supplied via notifications in form_valid exception catch.
        """
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
        return self.topic.entries.filter(date_created__gte=TIME_THRESHOLD_24H)

    def today_in_history(self):
        year = self.request.GET.get("year")
        try:
            if int(year) in YEAR_RANGE:
                now = timezone.now()
                return self.topic.entries.filter(date_created__year=year, date_created__month=now.month,
                                                 date_created__day=now.day)
        except (ValueError, OverflowError):
            return self.model.objects.none()

    def nice(self):
        return self.topic.entries.order_by("-vote_rate")

    def nicetoday(self):
        return self.today().order_by("-vote_rate")

    def search(self):
        keywords = self.request.GET.get("keywords")
        if keywords:
            if keywords.startswith("@"):
                try:
                    author = Author.objects.get(username=keywords[1:])
                    return self.topic.entries.filter(author=author)
                except Author.DoesNotExist:
                    return self.model.objects.none()
            else:
                # use postgresql to make searches more advanced if desired
                return self.topic.entries.filter(content__icontains=keywords)
        return self.model.objects.none()

    def following(self):
        queryset = None
        if self.request.user.is_authenticated:
            following = self.topic.followers.filter(author=self.request.user).first()

            if following:
                date = self.request.GET.get("d")

                try:
                    last_read = datetime.datetime.fromtimestamp(int(date))
                except (ValueError, TypeError, OSError):
                    last_read = None

                if last_read:
                    queryset = self.topic.entries.filter(date_created__gt=last_read).exclude(author=self.request.user)

            if not queryset:
                notifications.info(self.request, "pek bişey bulamadım açıkçası, buyrun hepsi")
                self.redirect = True
            else:
                following.read_at = timezone.now()
                following.save()
                notifications.info(self.request, f"{queryset.count()} tane entry")
                return queryset

        self.redirect = True

    def caylaklar(self):
        return self.topic.entries.filter(author__is_novice=True, date_created__gte=TIME_THRESHOLD_24H)

    def get_queryset(self):
        # filter queryset by self.view_mode
        queryset = None
        filtering_modes = ["today", "today_in_history", "nice", "nicetoday", "search", "following", "caylaklar"]

        if self.entry_permalink:
            queryset = self.topic.entries.filter(pk=self.entry_permalink)

        elif self.topic.exists:
            if self.view_mode in filtering_modes:
                queryset = getattr(self, self.view_mode)()
            else:
                # view mode is regular
                queryset = self.topic.entries.all()

        if queryset:
            return self._qs_filter(queryset)

        return self.model.objects.none()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        entries = context.get("object_list")
        context["topic"] = self.topic
        context["mode"] = self.view_mode
        context["entry_permalink"] = True if self.entry_permalink else False

        if self.topic.exists and len(entries) > 0:
            """
            Find subsequent and previous entries
            Get current page's first and last entry, and find the number of entries before and after by date.
            Using these count data, find what page next entry is located on.
            """
            previous_entries_count, previous_entries_page = 0, 0
            subsequent_entries_count, subsequent_entries_page = 0, 0
            show_subsequent, show_previous = False, False

            # view_mode specific settings
            if self.view_mode in ["today", "following", "caylaklar"]:
                show_previous = True
            elif self.view_mode in ["today_in_history", "entry_permalink", "search", "nicetoday"]:
                show_previous = True
                show_subsequent = True

            if show_subsequent or show_previous:
                first_entry_date = entries[0].date_created
                previous_entries_count = self._qs_filter(
                    self.topic.entries.filter(date_created__lt=first_entry_date, author__is_novice=False)).count()

            if show_previous:
                paginate_by = self.get_paginate_by()
                previous_entries_page = math.ceil(previous_entries_count / paginate_by)

            if show_subsequent:
                try:
                    queryset_size = len(entries)
                    last_entry_date = entries[queryset_size - 1].date_created
                    subsequent_entries_count = self._qs_filter(
                        self.topic.entries.filter(date_created__gt=last_entry_date, author__is_novice=False)).count()
                    if not subsequent_entries_count:
                        subsequent_entries_page = 0
                    else:
                        subsequent_entries_page = self._find_subsequent_page(previous_entries_count)
                except IndexError:
                    subsequent_entries_page = 0
                    subsequent_entries_count = 0

            context["previous_entries_count"] = previous_entries_count
            context["previous_entries_page"] = previous_entries_page
            context["subsequent_entries_count"] = subsequent_entries_count
            context["subsequent_entries_page"] = subsequent_entries_page

        elif not entries:
            # Parameters returned no corresponding entries, show ALL entries count to guide the user
            if self.view_mode in ["today", "today_in_history", "nice", "nicetoday", "search", "caylaklar"]:
                context["all_entries_count"] = self._qs_filter(self.topic.entries.all()).count()

        return context

    def dispatch(self, request, *args, **kwargs):
        search_redirect = self.get_topic()
        if search_redirect:
            return search_redirect

        #  Empty request (direct request to /topic/)
        elif self.topic is None:
            return redirect(reverse("home"))

        # view_mode is used to determine queryset
        if not self.view_mode:
            if request.GET.get("day") == "today":
                self.view_mode = "today"
            elif request.GET.get("year"):
                self.view_mode = "today_in_history"
            elif request.GET.get("a"):
                self.view_mode = request.GET.get("a")
            else:
                self.view_mode = "regular"

        return super().dispatch(request)

    def get_paginate_by(self, *args):
        if self.request.user.is_authenticated:
            return self.request.user.entries_per_page
        return ENTRIES_PER_PAGE_DEFAULT

    def render_to_response(self, context, **response_kwargs):
        # can only be caused by self.following()
        # this redirect is done here because we initially want to get the queryset first to decide if redirect is needed
        if self.redirect:
            return self._redirect_to_self()
        return super().render_to_response(context, **response_kwargs)

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
            try:
                entry_id = int(self.kwargs.get("entry_id"))
                self.topic = Topic.objects.get_or_pseudo(entry_id=entry_id)

                if self.request.user.is_authenticated:
                    entry = self.topic.entries.filter(pk=entry_id).first()
                    if entry.author in self.request.user.blocked.all():
                        raise Http404

                self.entry_permalink = entry_id
                self.view_mode = "entry_permalink"
            except (ValueError, OverflowError):
                raise Http404

        #  Search handling
        elif self.request.GET.get("q"):
            query = self.request.GET.get("q").strip()
            if query.startswith("@") and len(query) > 1:
                return redirect("user-profile", username=query[1:])

            elif query.startswith("#"):
                if query[1:].isdigit():
                    return redirect("entry-permalink", entry_id=query[1:])

            else:
                self.topic = Topic.objects.get_or_pseudo(unicode_string=query)
                if self.topic.exists:
                    return self._redirect_to_self()

        # No redirect
        return False

    def _redirect_to_self(self):
        #  Redirect to topic itself.
        return redirect(reverse("topic", kwargs={"slug": self.topic.slug}))

    def _find_subsequent_page(self, pages_before):
        is_on = pages_before + 1
        page_count = 0
        while is_on > 0:
            page_count += 1
            is_on -= self.get_paginate_by()
        if is_on == 0:
            page_count += 1
        return page_count

    def _qs_filter(self, queryset):
        #  Filter queryset to exclude drafts, blocked users etc.
        qs = queryset.exclude(is_draft=True)

        if self.view_mode not in ["caylaklar", "entry_permalink"]:
            qs = qs.exclude(author__is_novice=True)

        if self.request.user.is_authenticated:
            qs = qs.exclude(author__in=self.request.user.blocked.all())

        return qs
