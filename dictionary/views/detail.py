from contextlib import suppress

from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic import DetailView, ListView

from dictionary.conf import settings
from dictionary.forms.edit import MementoForm, SendMessageForm
from dictionary.models import Author, Conversation, ConversationArchive, Entry, Memento, Message
from dictionary.utils.decorators import cached_context
from dictionary.utils.managers import UserStatsQueryHandler, entry_prefetch
from dictionary.utils.mixins import IntegratedFormMixin


class Chat(LoginRequiredMixin, IntegratedFormMixin, DetailView):
    model = Conversation
    template_name = "dictionary/conversation/conversation.html"
    form_class = SendMessageForm
    context_object_name = "conversation"

    def get_recipient(self):
        return get_object_or_404(Author, slug=self.kwargs.get("slug"))

    def form_valid(self, form):
        recipient = self.get_recipient()
        message = Message.objects.compose(self.request.user, recipient, form.cleaned_data["body"])

        if not message:
            notifications.error(self.request, _("we couldn't send your message"))
            return self.form_invalid(form)

        return redirect(reverse("conversation", kwargs={"slug": self.kwargs.get("slug")}))

    def form_invalid(self, form):
        for err in form.non_field_errors() + form.errors.get("body", []):
            notifications.error(self.request, err)

        return super().form_invalid(form)

    def get_object(self, queryset=None):
        recipient = self.get_recipient()
        chat = self.model.objects.with_user(self.request.user, recipient)

        if chat is not None:
            # Mark read
            chat.messages.filter(sender=recipient, read_at__isnull=True).update(read_at=timezone.now())
            return chat

        raise Http404  # users haven't messaged each other yet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recipient = self.object.target
        is_blocked = self.request.user.blocked.filter(pk=recipient.pk).exists()  # causes 1 duplicate query
        can_send_message = False if is_blocked else self.request.user.can_send_message(recipient)

        context["recipient"] = recipient
        context["can_send_message"] = can_send_message
        context["is_blocked"] = is_blocked
        return context


class ChatArchive(LoginRequiredMixin, DetailView):
    template_name = "dictionary/conversation/conversation_archive.html"

    def get_object(self, queryset=None):
        return get_object_or_404(ConversationArchive, holder=self.request.user, slug=self.kwargs["slug"])


class LatestEntriesPaginator(Paginator):
    """
    Count of entries may have already been calculated. This means 1 less
    count(*) query.
    """

    def __init__(self, *args, **kwargs):
        self.cached_count = kwargs.pop("cached_count")
        super().__init__(*args, **kwargs)

    @cached_property
    def count(self):
        return self.cached_count


class UserProfile(IntegratedFormMixin, ListView):
    model = Entry
    paginate_by = settings.ENTRIES_PER_PAGE_PROFILE
    form_class = MementoForm
    template_name = "dictionary/user/profile.html"

    profile = None
    tab = None

    tabs = {
        "latest": {"label": _("entries"), "type": "entry"},
        "favorites": {"label": _("favorites"), "type": "entry"},
        "popular": {"label": _("most favorited"), "type": "entry"},
        "liked": {"label": _("most liked"), "type": "entry"},
        "weeklygoods": {"label": _("attracting entries of this week"), "type": "entry"},
        "beloved": {"label": _("beloved entries"), "type": "entry"},
        "authors": {"label": _("favorite authors"), "type": "author"},
        "recentlyvoted": {"label": _("recently voted"), "type": "entry"},
        "wishes": {"label": _("wishes"), "type": "topic"},
        "channels": {"label": _("contributed channels"), "type": "category"},
    }

    def form_valid(self, form):
        existing_memento = self.get_memento()
        body = form.cleaned_data.get("body")
        if existing_memento:
            if not body:
                existing_memento.delete()
                notifications.info(self.request, gettext("just deleted that"))
            else:
                existing_memento.body = body
                existing_memento.save()
        else:
            if not body:
                notifications.info(self.request, gettext("if only you could write down something"))
            else:
                memento = form.save(commit=False)
                memento.holder = self.request.user
                memento.patient = self.profile
                memento.save()
        return redirect(reverse("user-profile", kwargs={"slug": self.profile.slug}))

    def get_form_kwargs(self):
        # To populate textarea with existing memento data
        kwargs = super().get_form_kwargs()
        if self.request.method not in ("POST", "PUT"):
            memento = self.get_memento()
            if memento:
                kwargs.update({"data": {"body": memento.body}})
        return kwargs

    def get_paginator(self, *args, **kwargs):
        if self.tab == "latest":
            kwargs["cached_count"] = self.profile.entry_count
            return LatestEntriesPaginator(*args, **kwargs)

        return super().get_paginator(*args, **kwargs)

    def get_queryset(self):
        handler = UserStatsQueryHandler(self.profile, requester=self.request.user, order=True)
        qs = getattr(handler, self.tab)()
        tab_obj_type = self.tabs.get(self.tab)["type"]

        if tab_obj_type == "entry":
            return entry_prefetch(qs, self.request.user)

        if tab_obj_type in ("author", "topic", "category"):
            return qs

        raise Http404

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["tab"] = {"name": self.tab, **self.tabs.get(self.tab)}
        context["profile"] = self.profile
        context["novice_queue"] = self.get_novice_queue()
        return context

    def dispatch(self, request, *args, **kwargs):
        self.profile = get_object_or_404(Author, slug=self.kwargs.get("slug"), is_active=True)

        # Check accessibility
        if self.profile != self.request.user and any(
            (
                self.profile.is_frozen,
                self.profile.is_private,
                self.request.user.is_authenticated
                and (
                    self.profile.blocked.filter(pk=self.request.user.pk).exists()
                    or self.request.user.blocked.filter(pk=self.profile.pk).exists()
                ),
            )
        ):
            raise Http404

        tab = kwargs.get("tab")

        if tab is not None and tab not in self.tabs.keys():
            raise Http404

        self.tab = tab or "latest"
        return super().dispatch(request)

    def get_novice_queue(self):
        sender = self.request.user
        if (
            sender.is_authenticated
            and sender == self.profile
            and sender.is_novice
            and sender.application_status == "PN"
        ):
            queue = cached_context(prefix="nqu", vary_on_user=True, timeout=86400)(lambda user: user.novice_queue)
            return queue(user=sender)
        return None

    def get_memento(self):
        if self.request.user.is_authenticated:
            with suppress(Memento.DoesNotExist):
                return Memento.objects.get(holder=self.request.user, patient=self.profile)

        return None
