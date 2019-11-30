from decimal import Decimal

from django.contrib import messages as notifications
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView
from django.views.generic.edit import FormMixin
from django.urls import reverse

from ..forms.edit import SendMessageForm
from ..models import Entry, Author, Message, Conversation, Memento
from ..utils.settings import ENTRIES_PER_PAGE_PROFILE


class Chat(LoginRequiredMixin, FormMixin, DetailView):
    model = Conversation
    template_name = "conversation/conversation.html"
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

    def post(self, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)


def user_profile(request, username):
    """ THIS VIEW WILL BE CONVERTED TO CLASS BASED"""
    profile = get_object_or_404(Author, username=username)
    data = {"author": profile}

    if request.user.is_authenticated:
        if request.method == "POST":
            body = request.POST.get("memento")
            obj, created = Memento.objects.update_or_create(holder=request.user, patient=profile,
                                                            defaults={"body": body})
            data["memento"] = obj.body
            notifications.info(request, "kaydettik efendim")
            return redirect(reverse("user_profile", kwargs={"username": profile.username}))
        else:
            try:
                data["memento"] = Memento.objects.get(holder=request.user, patient=profile).body
            except Memento.DoesNotExist:
                pass

        if request.user in profile.blocked.all() or profile in request.user.blocked.all():
            raise Http404

        if request.user == profile and profile.is_novice and profile.application_status == "PN":
            if request.session.get("novice_queue"):
                data['novice_queue'] = request.session["novice_queue"]
            else:
                data['novice_queue'] = False

    page_tab = request.GET.get("t")

    if page_tab == "favorites":
        data['tab'] = "favorites"
        entries = profile.favorite_entries.filter(author__is_novice=False).order_by("-date_created")
    elif page_tab == "popular":
        data['tab'] = "popular"
        entries = Entry.objects_published.filter(author=profile, vote_rate__gt=Decimal("1"))
    else:
        data['tab'] = "entries"
        entries = Entry.objects_published.filter(author=profile).order_by("-date_created")

    paginator = Paginator(entries, ENTRIES_PER_PAGE_PROFILE)
    page = request.GET.get("page")
    entries_list = paginator.get_page(page)
    data['entries'] = entries_list

    return render(request, "user/user_profile.html", context=data)
