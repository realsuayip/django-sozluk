from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic import CreateView, FormView, UpdateView

from dictionary.forms.edit import EntryForm, PreferencesForm
from dictionary.models import Author, Comment, Entry, Topic
from dictionary.utils import time_threshold


class UserPreferences(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Author
    form_class = PreferencesForm
    template_name = "dictionary/user/preferences/index.html"
    success_message = _("settings are saved, dear")
    success_url = reverse_lazy("user_preferences")

    def get_object(self, queryset=None):
        return self.request.user

    def form_invalid(self, form):
        notifications.error(self.request, gettext("we couldn't handle your request. try again later."))
        return super().form_invalid(form)


class EntryCreateMixin:
    model = Entry
    form_class = EntryForm

    def form_valid(self, form):
        """
        User sent new entry, whose topic may or may not be existent. If topic
        exists, adds the entry and redirects to the entry permalink, otherwise
        the topic is created if the title is valid. Entry.save() sets created_by
        field of the topic.
        """

        draft_pk = self.request.POST.get("pub_draft_pk", "")
        publishing_draft = draft_pk.isdigit()

        if (not publishing_draft) and (self.topic.exists and self.topic.is_banned):
            # Cannot check is_banned before checking its existence.
            notifications.error(self.request, _("we couldn't handle your request. try again later."))
            return self.form_invalid(form)

        status = self.request.user.entry_publishable_status

        if status is not None:
            notifications.error(self.request, status, extra_tags="persistent")
            if publishing_draft:
                return redirect(reverse("entry_update", kwargs={"pk": int(draft_pk)}))
            return self.form_invalid(form)

        if publishing_draft:
            try:
                entry = Entry.objects_all.get(
                    pk=int(draft_pk), is_draft=True, author=self.request.user, topic__is_banned=False
                )
                entry.content = form.cleaned_data["content"]
                entry.is_draft = False
                entry.date_created = timezone.now()
                entry.date_edited = None
            except Entry.DoesNotExist:
                notifications.error(self.request, _("we couldn't handle your request. try again later."))
                return self.form_invalid(form)
        else:
            # Creating a brand new entry.
            entry = form.save(commit=False)
            entry.author = self.request.user

            if self.topic.exists:
                entry.topic = self.topic
            else:
                if not self.topic.valid:
                    notifications.error(self.request, _("curses to such a topic anyway."), extra_tags="persistent")
                    return self.form_invalid(form)

                entry.topic = Topic.objects.create_topic(title=self.topic.title)

        entry.save()
        notifications.info(self.request, _("the entry was successfully launched into stratosphere"))
        return redirect(reverse("entry-permalink", kwargs={"entry_id": entry.id}))

    def form_invalid(self, form):
        if form.errors:
            for err in form.errors["content"]:
                notifications.error(self.request, err, extra_tags="persistent")

        return super().form_invalid(form)


class EntryCreate(LoginRequiredMixin, EntryCreateMixin, FormView):
    template_name = "dictionary/edit/entry_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.extra_context = {"title": self.request.POST.get("title", "")}
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["recent_drafts"] = (
            Entry.objects_all.filter(
                Q(date_created__gte=time_threshold(hours=24)) | Q(date_edited__gte=time_threshold(hours=24)),
                is_draft=True,
                author=self.request.user,
            )
            .select_related("topic")
            .only("topic__title", "date_created", "date_edited")
            .alias(last_edited=Coalesce(F("date_edited"), F("date_created")))
            .order_by("-last_edited")[:5]
        )
        return context

    def form_valid(self, form):
        if not self.request.POST.get("pub_draft_pk", "").isdigit():
            # Topic object is only required if not publishing a draft.
            self.topic = Topic.objects.get_or_pseudo(unicode_string=self.extra_context.get("title"))  # noqa
        return super().form_valid(form)


class EntryUpdate(LoginRequiredMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = "dictionary/edit/entry_update.html"
    context_object_name = "entry"

    def form_valid(self, form):
        entry = form.save(commit=False)

        if self.request.user.is_suspended or entry.topic.is_banned:
            notifications.error(self.request, gettext("you lack the required permissions."))
            return super().form_invalid(form)

        if entry.is_draft:
            status = self.request.user.entry_publishable_status

            if status is not None:
                notifications.error(self.request, status, extra_tags="persistent")
                return super().form_invalid(form)

            entry.is_draft = False
            entry.date_created = timezone.now()
            entry.date_edited = None
            notifications.info(self.request, gettext("the entry was successfully launched into stratosphere"))
        else:
            entry.date_edited = timezone.now()

        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors["content"]:
            notifications.error(self.request, error)

        return super().form_invalid(form)

    def get_queryset(self):
        return Entry.objects_all.filter(author=self.request.user)


class CommentMixin(LoginRequiredMixin, SuccessMessageMixin):
    model = Comment
    fields = ("content",)
    template_name = "dictionary/edit/comment_form.html"

    def form_invalid(self, form):
        for error in form.errors["content"]:
            notifications.error(self.request, error)
        return super().form_invalid(form)


class CommentCreate(CommentMixin, CreateView):
    success_message = _("the comment was successfully launched into stratosphere")
    entry = None

    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(Entry.objects_published, pk=self.kwargs.get("pk"))

        if not (
            request.user.has_perm("dictionary.can_comment") and self.entry.topic.is_ama and request.user.is_accessible
        ):
            raise Http404

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entry"] = self.entry
        return context

    def form_valid(self, form):
        comment = form.save(commit=False)
        comment.author = self.request.user
        comment.entry = self.entry
        comment.save()
        return super().form_valid(form)


class CommentUpdate(CommentMixin, UpdateView):
    success_message = _("the comment has been updated")

    def get_object(self, queryset=None):
        return get_object_or_404(Comment, pk=self.kwargs.get(self.pk_url_kwarg), author=self.request.user)

    def form_valid(self, form):
        if self.request.POST.get("delete"):
            self.object.delete()
            notifications.success(self.request, gettext("the comment has been deleted"))
            return redirect(self.object.entry.get_absolute_url())

        if not self.request.user.is_accessible:
            notifications.error(
                self.request, gettext("you lack the permissions to edit this comment. you might as well delete it?")
            )
            return self.form_invalid(form)

        comment = form.save(commit=False)
        comment.date_edited = timezone.now()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entry"] = self.object.entry
        context["updating"] = True
        return context
