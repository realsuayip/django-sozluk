import datetime

from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView

from ..forms.edit import MementoForm, SendMessageForm
from ..models import Author, Conversation, Entry, Memento, Message
from ..utils.mixins import IntegratedFormMixin
from ..utils.settings import ENTRIES_PER_PAGE_PROFILE


class Chat(LoginRequiredMixin, IntegratedFormMixin, DetailView):
    model = Conversation
    template_name = "dictionary/conversation/conversation.html"
    form_class = SendMessageForm
    context_object_name = "conversation"

    def get_recipient(self):
        recipient = get_object_or_404(Author, username=self.kwargs.get("username"))
        return recipient

    def form_valid(self, form):
        recipient = self.get_recipient()
        msg = Message.objects.compose(self.request.user, recipient, form.cleaned_data['body'])
        if not msg:
            notifications.error(self.request, "mesajınızı gönderemedik ne yazık ki")
        return redirect(reverse("conversation", kwargs={"username": self.kwargs.get("username")}))

    def form_invalid(self, form):
        if form.non_field_errors():
            for msg in form.non_field_errors():
                notifications.error(self.request, msg)

        return redirect(reverse("conversation", kwargs={"username": self.kwargs.get("username")}))

    def get_object(self, queryset=None):
        recipient = self.get_recipient()
        chat = self.model.objects.with_user(self.request.user, recipient)
        if chat:
            unread_messages = chat.messages.filter(sender=recipient, read_at__isnull=True)
            if unread_messages:
                for msg in unread_messages:
                    msg.mark_read()

            return chat

        raise Http404  # users haven't messsaged each other yet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recipient'] = self.get_recipient()
        return context


class UserProfile(IntegratedFormMixin, ListView):
    model = Entry
    paginate_by = ENTRIES_PER_PAGE_PROFILE
    form_class = MementoForm
    template_name = "dictionary/user/profile.html"

    profile = None
    tab = None

    # @formatter:off
    tabs = {
        "latest": {"label": "entry'ler", "type": "entry"},
        "favorites": {"label": "favorileri", "type": "entry"},
        "popular": {"label": "en çok favorilenenleri", "type": "entry"},
        "liked": {"label": "en beğenilenleri", "type": "entry"},
        "weeklygoods": {"label": "bu hafta dikkat çekenleri", "type": "entry"},
        "beloved": {"label": "el emeği göz nuru", "type": "entry"},
        "authors": {"label": "favori yazarları", "type": "author"},
    }  # @formatter:on

    def form_valid(self, form):
        existing_memento = self.get_memento()
        body = form.cleaned_data.get("body")
        if existing_memento:
            if not body:
                existing_memento.delete()
                notifications.info(self.request, "sildim ben onu")
            else:
                existing_memento.body = body
                existing_memento.save()
        else:
            if not body:
                notifications.info(self.request, "çeşke bi şeyler yazsaydın")
            else:
                memento = form.save(commit=False)
                memento.holder = self.request.user
                memento.patient = self.profile
                memento.save()
        return redirect(reverse("user-profile", kwargs={"username": self.profile.username}))

    def get_form_kwargs(self):
        # To populate textarea with existing memento data
        kwargs = super().get_form_kwargs()
        if self.request.method not in ('POST', 'PUT'):
            memento = self.get_memento()
            if memento:
                kwargs.update({"data": {"body": memento.body}})
        return kwargs

    def get_queryset(self):
        qs = getattr(self, self.tab)()
        tab_obj_type = self.tabs.get(self.tab)['type']

        if tab_obj_type == "entry":
            return qs.select_related("author", "topic").prefetch_related("favorited_by", "downvoted_by", "upvoted_by")

        if tab_obj_type == "author":
            return qs

        raise Http404

    def latest(self):
        # default tab
        return Entry.objects_published.filter(author=self.profile).order_by("-date_created")

    def favorites(self):
        return self.profile.favorite_entries.filter(author__is_novice=False).order_by("-entryfavorites__date_created")

    def popular(self):
        return Entry.objects_published.filter(author=self.profile).annotate(count=Count("favorited_by")).order_by(
            "-count")

    def liked(self):
        return Entry.objects_published.filter(author=self.profile).order_by("-vote_rate")

    def weeklygoods(self):
        return self.liked().filter(date_created__gte=timezone.now() - datetime.timedelta(days=7))

    def beloved(self):
        return Entry.objects_published.filter(author=self.profile, favorited_by__in=[self.profile]).order_by(
            "-date_created")

    def authors(self):
        favorites = self.profile.favorite_entries.all()
        return Author.objects.filter(entry__in=favorites).annotate(frequency=Count("entry")).filter(
            frequency__gt=1).order_by("-frequency")[:10]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab"] = {"name": self.tab, **self.tabs.get(self.tab)}
        context["profile"] = self.profile
        context['novice_queue'] = self.get_novice_queue()
        return context

    def dispatch(self, request, *args, **kwargs):
        self.profile = get_object_or_404(Author, username=self.kwargs.get("username"))

        # Check accessibility
        if self.profile.is_frozen or self.profile.is_private:
            raise Http404

        # Check accessibility (block status)
        if self.request.user.is_authenticated:
            if self.request.user in self.profile.blocked.all() or self.profile in self.request.user.blocked.all():
                raise Http404

        # Set-up tab
        tab_requested = request.GET.get("t", "latest")
        self.tab = tab_requested if tab_requested in self.tabs.keys() else "latest"

        return super().dispatch(request)

    def get_novice_queue(self):
        if self.request.user.is_authenticated:
            if self.request.user == self.profile and self.profile.is_novice and self.profile.application_status == "PN":
                if self.request.session.get("novice_queue"):
                    return self.request.session["novice_queue"]
        return None

    def get_memento(self):
        if self.request.user.is_authenticated:
            try:
                return Memento.objects.get(holder=self.request.user, patient=self.profile)
            except Memento.DoesNotExist:
                return None
        return None
