from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from django.views.generic import CreateView, UpdateView

from ..forms.edit import EntryForm, PreferencesForm
from ..models import Author, Comment, Entry


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
