from django.contrib import admin
from django.contrib import messages as notifications
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.mail import send_mail
from django.db.models import Case, IntegerField, Q, When
from django.shortcuts import get_object_or_404, redirect, reverse
from django.views.generic import ListView

from ...models import Author, Entry, Message
from ...utils import get_generic_superuser, time_threshold
from ...utils.admin import log_admin
from ...utils.settings import NOVICE_ACCEPTED_MESSAGE, NOVICE_REJECTED_MESSAGE


def novice_list(limit=None):
    novice_queryset = Author.objects.filter(last_activity__isnull=False, is_novice=True,
                                            application_status="PN").annotate(
        activity=Case(When(Q(last_activity__gte=time_threshold(hours=24)), then=2),
                      When(Q(last_activity__lte=time_threshold(hours=24)), then=1),
                      output_field=IntegerField(), )).order_by("-activity", "application_date")

    if limit is not None:
        return novice_queryset[:limit]
    return novice_queryset


class NoviceList(PermissionRequiredMixin, ListView):
    # View to list top 10 novices.
    model = Author
    template_name = "dictionary/admin/novices.html"
    permission_required = "dictionary.can_activate_user"

    def get_queryset(self):
        return novice_list(10)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(admin.site.each_context(self.request))
        context["title"] = "Çaylak onay listesi"
        context["novice_count"] = novice_list().count()
        return context


class NoviceLookup(PermissionRequiredMixin, ListView):
    """
    View to accept or reject a novice application. Lists first 10 entries of the novice user. Users will get mail
    and a message indicating the result of their application. A LogEntry object is created for this action.
    """

    model = Entry
    template_name = "dictionary/admin/novice_lookup.html"
    permission_required = "dictionary.can_activate_user"
    context_object_name = "entries"

    novice = None

    def dispatch(self, request, *args, **kwargs):
        self.novice = get_object_or_404(Author, username=self.kwargs.get("username"))
        novices = novice_list()

        if self.novice not in novices:
            notifications.error(self.request, "kullanıcı çaylak onay listesinde değil.")
            self.novice = None
        elif self.novice not in novices[:10]:
            self.novice = None
            notifications.error(self.request, "kullanıcı çaylak onay listesinin başında değil")

        if self.novice is None:
            return redirect(reverse("admin:novice_list"))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        first_ten_entries = Entry.objects_published.filter(author=self.novice).order_by("id")[:10]
        return first_ten_entries

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(admin.site.each_context(self.request))
        context["title"] = f"{self.novice.username} isimli çaylağın ilk 10 entry'si"
        context["next"] = self.get_next_username()
        return context

    def post(self, *args, **kwargs):
        operation = self.request.POST.get("operation")

        if operation not in ["accept", "decline"]:
            notifications.error(self.request, "Geçersiz bir işlem seçtiniz.")
            return redirect(reverse("admin:novice_lookup", kwargs={"username": self.novice.username}))

        if operation == "accept":
            self.accept_application()
        elif operation == "decline":
            self.decline_application()

        if self.request.POST.get("submit_type") == "redirect_back":
            return redirect(reverse("admin:novice_list"))

        return redirect(reverse("admin:novice_lookup", kwargs={"username": self.request.POST.get("submit_type")}))

    def get_next_username(self):
        next_novice = None
        # Get next novice on the list and return it's username, required for 'save and continue'
        if self.novice.last_activity >= time_threshold(hours=24):
            next_novice = Author.objects.filter(is_novice=True, application_status="PN",
                                                last_activity__gt=time_threshold(hours=24),
                                                application_date__gt=self.novice.application_date).order_by(
                "application_date").first()

        if not next_novice:
            # There was no user with latest activity. Check for non-active ones.
            next_novice = Author.objects.filter(is_novice=True, application_status="PN",
                                                last_activity__lt=time_threshold(hours=24),
                                                application_date__gt=self.novice.application_date).order_by(
                "application_date").first()

        next_username = next_novice.username if next_novice else None
        return next_username

    def accept_application(self):
        user = self.novice
        user.application_status = Author.APPROVED
        user.is_novice = False
        user.save()
        admin_info_msg = f"{user.username} nickli kullanıcının yazarlık talebi kabul edildi"
        log_admin(admin_info_msg, self.request.user, Author, user)
        Message.objects.compose(get_generic_superuser(), user, NOVICE_ACCEPTED_MESSAGE.format(user.username))
        send_mail('yazarlık başvurunuz kabul edildi', NOVICE_ACCEPTED_MESSAGE.format(user.username),
                  'Django Sözlük <correct@email.com>', [user.email], fail_silently=False)
        notifications.success(self.request, admin_info_msg)
        return True

    def decline_application(self):
        user = self.novice
        Entry.objects_published.filter(author=user).delete()  # does not trigger model's delete()
        user.application_status = Author.ON_HOLD
        user.application_date = None
        user.save()
        admin_info_msg = f"{user.username} nickli kullanıcının yazarlık talebi kabul reddedildi"
        log_admin(admin_info_msg, self.request.user, Author, user)
        Message.objects.compose(get_generic_superuser(), user, NOVICE_REJECTED_MESSAGE.format(user.username))
        send_mail('yazarlık başvurunuz reddedildi', NOVICE_REJECTED_MESSAGE.format(user.username),
                  'Django Sözlük <correct@email.com>', [user.email], fail_silently=False)
        notifications.success(self.request, admin_info_msg)
        return True
