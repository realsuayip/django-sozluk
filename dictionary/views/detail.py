from contextlib import suppress

from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView

from ..forms.edit import MementoForm, SendMessageForm
from ..models import Author, Conversation, ConversationArchive, Entry, Memento, Message
from ..utils.managers import UserStatsQueryHandler
from ..utils.mixins import IntegratedFormMixin
from ..utils.settings import ENTRIES_PER_PAGE_PROFILE


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
            notifications.error(self.request, "mesajınızı gönderemedik")
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

        raise Http404  # users haven't messsaged each other yet

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recipient"] = self.object.target
        context["can_send_message"] = self.request.user.can_send_message(self.object.target)
        context["is_blocked"] = self.request.user.blocked.filter(pk=self.object.target.pk).exists()
        return context


class ChatArchive(LoginRequiredMixin, DetailView):
    model = ConversationArchive
    template_name = "dictionary/conversation/conversation_archive.html"


class UserProfile(IntegratedFormMixin, ListView):
    model = Entry
    paginate_by = ENTRIES_PER_PAGE_PROFILE
    form_class = MementoForm
    template_name = "dictionary/user/profile.html"

    profile = None
    tab = None

    tabs = {
        "latest": {"label": "entry'ler", "type": "entry"},
        "favorites": {"label": "favorileri", "type": "entry"},
        "popular": {"label": "en çok favorilenenleri", "type": "entry"},
        "liked": {"label": "en beğenilenleri", "type": "entry"},
        "weeklygoods": {"label": "bu hafta dikkat çekenleri", "type": "entry"},
        "beloved": {"label": "el emeği göz nuru", "type": "entry"},
        "authors": {"label": "favori yazarları", "type": "author"},
        "recentlyvoted": {"label": "son oylananları", "type": "entry"},
        "wishes": {"label": "ukteleri", "type": "topic"},
        "channels": {"label": "katkıda bulunduğu kanallar", "type": "category"},
    }

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
        return redirect(reverse("user-profile", kwargs={"slug": self.profile.slug}))

    def get_form_kwargs(self):
        # To populate textarea with existing memento data
        kwargs = super().get_form_kwargs()
        if self.request.method not in ("POST", "PUT"):
            memento = self.get_memento()
            if memento:
                kwargs.update({"data": {"body": memento.body}})
        return kwargs

    def get_queryset(self):
        handler = UserStatsQueryHandler(self.profile, order=True)
        qs = getattr(handler, self.tab)()
        tab_obj_type = self.tabs.get(self.tab)["type"]

        if tab_obj_type == "entry":
            base = qs.select_related("author", "topic")

            if self.request.user.is_authenticated:
                return base.prefetch_related(
                    Prefetch(
                        "favorited_by",
                        queryset=Author.objects_accessible.only("pk").exclude(pk__in=self.request.user.blocked.all()),
                    )
                )

            return base

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
        if (
            self.profile.is_frozen
            or self.profile.is_private
            or (
                self.request.user.is_authenticated
                and (
                    self.profile.blocked.filter(pk=self.request.user.pk).exists()
                    or self.request.user.blocked.filter(pk=self.profile.pk).exists()
                )
            )
        ):
            raise Http404

        tab = kwargs.get("tab")

        if tab is not None and tab not in self.tabs.keys():
            raise Http404

        self.tab = tab or "latest"
        return super().dispatch(request)

    def get_novice_queue(self):
        user = self.request.user
        if (
            user.is_authenticated
            and user == self.profile
            and user.is_novice
            and user.application_status == "PN"
            and (queue := self.request.session.get("novice_queue"))
        ):
            return queue
        return None

    def get_memento(self):
        if self.request.user.is_authenticated:
            with suppress(Memento.DoesNotExist):
                return Memento.objects.get(holder=self.request.user, patient=self.profile)

        return None
