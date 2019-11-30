import random

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, F, Max, Case, When, IntegerField
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.generic import ListView, TemplateView
from django.utils.decorators import method_decorator

from ..models import Category, Topic, Conversation, TopicFollowing
from ..utils.managers import TopicListManager
from ..utils.settings import TOPICS_PER_PAGE, YEAR_RANGE, nondb_categories


class PeopleList(LoginRequiredMixin, TemplateView):
    template_name = "people.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blocked'] = self.request.user.blocked
        context['following'] = self.request.user.following
        return context


class ConversationList(LoginRequiredMixin, ListView):
    model = Conversation
    allow_empty = True
    paginate_by = 3
    template_name = "conversation/inbox.html"
    context_object_name = "conversations"

    def get_queryset(self):
        return Conversation.objects.list_for_user(self.request.user)


class ActivityList(LoginRequiredMixin, ListView):
    model = TopicFollowing
    template_name = "activity.html"
    context_object_name = "topics_following"

    def get_queryset(self):
        return TopicFollowing.objects.filter(author=self.request.user).annotate(
            latest=Max("topic__entries__date_created"),
            is_read=Case(When(Q(latest__gt=F("read_at")), then=1), When(Q(latest__lt=F("read_at")), then=2),
                         output_field=IntegerField()), ).order_by("is_read", "-read_at")


class CategoryList(ListView):
    model = Category
    template_name = "category_list.html"
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
    template_name = "topic_list.html"
    paginate_by = TOPICS_PER_PAGE
    refresh_count = 0
    slug_identifier = None

    def get_queryset(self):
        year = None
        slug = self.kwargs['slug']
        if slug == "tarihte-bugun":

            if self.request.GET.get("year"):
                year = self.request.GET.get("year")
                self.request.session["year"] = year
            else:
                year = self.request.session.get("year")

            if not year:
                year = random.choice(YEAR_RANGE)
                self.request.session["year"] = year

            try:
                if int(year) not in YEAR_RANGE:
                    year = None
            except ValueError:
                year = None

        if slug == "bugun" and not self.request.user.is_authenticated:
            return self.model.objects.none()

        manager = TopicListManager(self.request.user, slug, extend=True, year=year)
        self.refresh_count = manager.refresh_count
        self.slug_identifier = manager.slug_identifier
        return manager.serialized

    def get_context_data(self, **kwargs):
        slug = self.kwargs['slug']
        nondb_safename = {"bugun": "bugün", "gundem": "gündem", "basiboslar": "başıboşlar", "takip": "takip",
                          "tarihte-bugun": "tarihte bugün", "kenar": "kenar", "caylaklar": "çaylaklar",
                          "debe": "dünün en beğenilen entry'leri", }
        if slug in nondb_categories:
            title = nondb_safename[slug]
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

    @method_decorator(login_required)
    def post(self, *args, **kwargs):
        if self.kwargs['slug'] == "bugun":
            # reset cache (refresh button mobile click event)
            manager = TopicListManager(self.request.user, "bugun", extend=True)
            manager.delete_cache()
            return redirect(self.request.path)
        return HttpResponseBadRequest()
