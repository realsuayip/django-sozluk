from datetime import timedelta
from django.contrib import messages as notifications
from django.utils import timezone
from django.shortcuts import redirect

from ...models import Author, Message
from ...utils import log_admin, parse_date_or_none, get_generic_superuser
from ...utils.views import IntermediateActionView


class SuspendUser(IntermediateActionView):
    permission_required = ("dictionary.suspend_user", "dictionary.change_author")
    model = Author
    page_title = "Yazarları askıya al"
    template_name = "dictionary/admin/actions/suspend_user.html"

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
            self.object_list.update(suspended_until=suspended_until)

            superuser = get_generic_superuser()
            information = request.POST.get("information", "Bilgi verilmedi.")

            for user in self.object_list:
                Message.objects.compose(superuser, user, f"Hesabınız askıya alındı. Yetkili mesajı: {information}. "
                                                         f"Profil sayfanızda hesabınızın tekrar aktifleştirilmesi için "
                                                         f"kalan süreyi görebilirsiniz.")
                log_admin(f"Suspended until {suspended_until}", request.user, Author, user)

            notifications.success(request, f"{self.object_list.count()} yazar askıya alındı.")
        else:
            notifications.error(request, "Geçersiz bir süre seçtiniz.")

        return redirect(self.get_changelist_url())


class UnsuspendUser(IntermediateActionView):
    permission_required = ("dictionary.suspend_user", "dictionary.change_author")
    model = Author
    page_title = "Yazarların askıya alınmasını durdur"
    template_name = "dictionary/admin/actions/unsuspend_user.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(suspended_until__gt=timezone.now())

    def post(self, request):
        confirmed = request.POST.get("post") == "yes"
        if confirmed:
            object_list_raw = list(self.object_list)
            self.object_list.update(suspended_until=None)

            for user in object_list_raw:
                log_admin(f"Removed suspension", request.user, Author, user)

            notifications.success(request, f"{len(object_list_raw)} yazarın askıdan alınma durumu sona erdi.")
        else:
            notifications.error(request, "İşlem gerçekleştirilemedi.")
        return redirect(self.get_changelist_url())
