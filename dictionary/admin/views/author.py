from datetime import timedelta

from django.contrib import messages as notifications
from django.shortcuts import redirect
from django.utils import timezone

from ...models import Author, Message
from ...utils import get_generic_superuser, parse_date_or_none
from ...utils.admin import logentry_bulk_create, logentry_instance
from ...utils.views import IntermediateActionView


class SuspendUser(IntermediateActionView):
    """
    View for user suspension intermediate page. Admin provides suspension time from 'time_choices' and also provides
    some information. For each suspended user, a LogEntry object is created. get_queryset is not modified so it is
    possible to select already suspended users, but latest submission will be taken into account. Note that composing
    a message to each banned user is an expensive action, large inputs (> 100) may take time. (~7 sec for 800 objects)
    """
    permission_required = ("dictionary.suspend_user", "dictionary.change_author")
    model = Author
    page_title = "Yazarları askıya al"
    template_name = "dictionary/admin/actions/suspend_user.html"
    max_input = 100

    def post(self, request):
        # @formatter:off
        time_choices = {
            "D1": timedelta(days=1),
            "W1": timedelta(days=7),
            "W2": timedelta(days=14),
            "M1": timedelta(days=30),
            "M3": timedelta(days=90),
            "PM": None,
        }  # @formatter:on

        choice = request.POST.get("suspension_time")

        if choice in time_choices.keys():
            if choice == "PM":
                suspended_until = parse_date_or_none("01.01.2038")
            else:
                suspended_until = timezone.now() + time_choices[choice]

            # Evaluate it immediately because it needs to be iterated and we need to call len()
            user_list_raw = list(self.get_object_list())

            # Get and parse information for suspension
            action_information = request.POST.get("information", "Bilgi verilmedi.")
            message_for_user = f"Hesabınız askıya alındı. Yetkili mesajı: {action_information}. " \
                               f"Profil sayfanızda hesabınızın tekrar aktifleştirilmesi için " \
                               f"kalan süreyi görebilirsiniz."
            message_for_log = f"Suspended until {suspended_until}, information: {action_information}"

            log_list = []  # Reserve list that hold instances for bulk creation

            # Set new suspended_until and append instances to reserved lists
            for user in user_list_raw:
                user.suspended_until = suspended_until
                log_list.append(logentry_instance(message_for_log, request.user, Author, user))
                Message.objects.compose(get_generic_superuser(), user, message_for_user)

            # Bulk creation/updates
            Author.objects.bulk_update(user_list_raw, ['suspended_until'])  # Update Author, does not call save()
            logentry_bulk_create(log_list)  # Log user suspension for admin history

            notifications.success(request, f"{len(user_list_raw)} yazar askıya alındı.")
        else:
            notifications.error(request, "Geçersiz bir süre seçtiniz.")

        return redirect(self.get_changelist_url())


class UnsuspendUser(IntermediateActionView):
    # Same procedures as SuspendUser.
    permission_required = ("dictionary.suspend_user", "dictionary.change_author")
    model = Author
    page_title = "Yazarların askıya alınmasını durdur"
    template_name = "dictionary/admin/actions/unsuspend_user.html"

    def get_queryset(self):
        # Select only suspended users.
        queryset = super().get_queryset()
        return queryset.filter(suspended_until__gt=timezone.now())

    def post(self, request):
        confirmed = request.POST.get("post") == "yes"
        if confirmed:
            user_list_raw = list(self.get_object_list())

            log_list = []

            for user in user_list_raw:
                user.suspended_until = None
                log_list.append(logentry_instance("Removed suspension", request.user, Author, user))

            Author.objects.bulk_update(user_list_raw, ['suspended_until'])
            logentry_bulk_create(log_list)

            notifications.success(request, f"{len(user_list_raw)} yazarın askıdan alınma durumu sona erdi.")
        else:
            notifications.error(request, "İşlem gerçekleştirilemedi.")
        return redirect(self.get_changelist_url())
