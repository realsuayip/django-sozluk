from decimal import Decimal

from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormMixin
from django.urls import reverse

from ..forms.edit import SendMessageForm, MementoForm
from ..models import Entry, Author, Message, Conversation, Memento
from ..utils.mixins import FormPostHandlerMixin
from ..utils.settings import ENTRIES_PER_PAGE_PROFILE


class Chat(LoginRequiredMixin, DetailView, FormPostHandlerMixin, FormMixin):
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

    def get_object(self, queryset=None):
        recipient = self.get_recipient()
        chat = self.model.objects.with_user(self.request.user, recipient)
        if chat:
            unread_messages = chat.messages.filter(sender=recipient, read_at__isnull=True)
            if unread_messages:
                for msg in unread_messages:
                    msg.mark_read()
        return chat

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recipient'] = self.get_recipient()
        return context


class UserProfile(ListView, FormPostHandlerMixin, FormMixin):
    model = Entry
    paginate_by = ENTRIES_PER_PAGE_PROFILE
    context_object_name = "entries"
    form_class = MementoForm
    template_name = "dictionary/user/profile.html"

    profile = None
    tab = None

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
        if self.tab == "favorites":
            qs = self.profile.favorite_entries.filter(author__is_novice=False).order_by("-date_created")
        elif self.tab == "popular":
            qs = Entry.objects_published.filter(author=self.profile, vote_rate__gt=Decimal("1"))
        else:
            qs = Entry.objects_published.filter(author=self.profile).order_by("-date_created")

        return qs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab"] = self.tab
        context["profile"] = self.profile
        context['novice_queue'] = self.get_novice_queue()
        return context

    def dispatch(self, request, *args, **kwargs):
        self.profile = get_object_or_404(Author, username=self.kwargs.get("username"))
        self.tab = request.GET.get("t")

        if self.request.user.is_authenticated:
            if self.request.user in self.profile.blocked.all() or self.profile in self.request.user.blocked.all():
                raise Http404

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
