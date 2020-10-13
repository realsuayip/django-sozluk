from django.contrib import admin
from django.contrib import messages as notifications
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, reverse
from django.utils.translation import gettext as _
from django.views.generic import ListView

from dictionary.conf import settings
from dictionary.models import Author, Entry, Message
from dictionary.utils import get_generic_superuser
from dictionary.utils.admin import log_admin


class NoviceList(PermissionRequiredMixin, ListView):
    """View to list top 100 novices."""

    model = Author
    template_name = "admin/novices.html"
    permission_required = "dictionary.can_activate_user"

    def get_queryset(self):
        return Author.in_novice_list.get_ordered(100)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(admin.site.each_context(self.request))
        context["title"] = _("Novice review list")
        context["novice_count"] = Author.in_novice_list.get_ordered().count()
        return context


class NoviceLookup(PermissionRequiredMixin, ListView):
    """
    View to accept or reject a novice application. Lists first 10 entries of the
    novice user. Users will get mail and a message indicating the result of
    their application. A LogEntry object is created for this action.
    """

    model = Entry
    template_name = "admin/novice_lookup.html"
    permission_required = "dictionary.can_activate_user"
    context_object_name = "entries"

    novice = None

    def dispatch(self, request, *args, **kwargs):
        self.novice = get_object_or_404(Author, username=self.kwargs.get("username"))
        novices = Author.in_novice_list.get_ordered()

        if not novices.filter(pk=self.novice.pk).exists():
            notifications.error(self.request, _("The user is not on the novice list."))
            self.novice = None
        elif self.novice not in novices[:100]:
            self.novice = None
            notifications.error(self.request, _("The user is not at the top of the novice list."))

        if self.novice is None:
            return redirect(reverse("admin:novice_list"))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.novice.entry_set(manager="objects_published").order_by("pk")[:10]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(admin.site.each_context(self.request))
        context["title"] = _("First ten entries of: %(username)s") % {"username": self.novice.username}
        return context

    def post(self, *args, **kwargs):
        operation = self.request.POST.get("operation")

        if operation not in ["accept", "decline"]:
            notifications.error(self.request, _("The selected operation was invalid."))
            return redirect(reverse("admin:novice_lookup", kwargs={"username": self.novice.username}))

        if operation == "accept":
            self.accept_application()
        elif operation == "decline":
            self.decline_application()

        return redirect(reverse("admin:novice_list"))

    def accept_application(self):
        # Alter the user status
        user = self.novice
        user.application_status = Author.Status.APPROVED
        user.is_novice = False
        user.save()

        # Log admin info
        admin_info_msg = _("Authorship of the user '%(username)s' was approved.") % {"username": user.username}
        log_admin(admin_info_msg, self.request.user, Author, user)

        # Send information messages to the user
        user_info_msg = _(
            "dear %(username)s, congratulations! your application"
            " of authorship has been approved. you can utilize your"
            " authorship by logging in."
        ) % {"username": user.username}
        Message.objects.compose(get_generic_superuser(), user, user_info_msg)
        user.email_user(_("your authorship has been approved"), user_info_msg, settings.FROM_EMAIL)

        notifications.success(self.request, admin_info_msg)
        return True

    def decline_application(self):
        # Alter the user status & delete entries
        user = self.novice
        Entry.objects_published.filter(author=user).delete()  # does not trigger model's delete()
        user.application_status = Author.Status.ON_HOLD
        user.application_date = None
        user.save()

        # Log admin info
        admin_info_msg = _("Authorship of the user '%(username)s' was rejected.") % {"username": user.username}
        log_admin(admin_info_msg, self.request.user, Author, user)

        # Send information messages to the user
        user_info_msg = _(
            "dear %(username)s, your application of authorship has been"
            " rejected and all of your entries has been deleted. if you"
            " fill up 10 entries, you will be admitted to novice list again."
        ) % {"username": user.username}
        Message.objects.compose(get_generic_superuser(), user, user_info_msg)
        user.email_user(_("your authorship has been rejected"), user_info_msg, settings.FROM_EMAIL)

        notifications.success(self.request, admin_info_msg)
        return True
