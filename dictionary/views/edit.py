from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import UpdateView

from ..forms.edit import EntryForm, PreferencesForm
from ..models import Author, Entry


class UserPreferences(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Author
    form_class = PreferencesForm
    template_name = "dictionary/user/preferences/index.html"
    success_message = "kaydettik efendim"
    success_url = reverse_lazy("user_preferences")

    def get_object(self, queryset=None):
        return self.request.user

    def form_invalid(self, form):
        notifications.error(self.request, "bir şeyler ters gitti")
        return super().form_invalid(form)


class EntryUpdate(LoginRequiredMixin, UpdateView):
    model = Entry
    form_class = EntryForm
    template_name = "dictionary/edit/entry_update.html"
    context_object_name = "entry"

    def get_success_url(self):
        if self.object.is_draft:
            notifications.info(self.request, "yazdım bir kenara")
            return reverse("entry_update", kwargs={"pk": self.object.pk})

        return reverse("entry-permalink", kwargs={"entry_id": self.object.pk})

    def form_valid(self, form):
        entry_is_draft_initial = self.object.is_draft  # returns True is the object is draft
        entry = form.save(commit=False)

        if entry_is_draft_initial:
            # Updating never-published entry (draft)
            if not entry.is_draft:  # Entry is being published by user
                # Suspended users can't publish their drafts
                if self.request.user.is_suspended:
                    entry.is_draft = True
                entry.date_created = timezone.now()
        else:
            # Updating published entry
            entry.is_draft = False
            entry.date_edited = timezone.now()

        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors["content"]:
            notifications.error(self.request, error)

        return super().form_invalid(form)

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        obj = get_object_or_404(Entry.objects_all, pk=pk)

        if obj.author != self.request.user:
            raise Http404
        return obj
