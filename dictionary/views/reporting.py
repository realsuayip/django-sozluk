from django.contrib import messages as notifications
from django.shortcuts import reverse
from django.views.generic import CreateView

from ..models import GeneralReport


class GeneralReportView(CreateView):
    #  todo create session to hinder many requests
    model = GeneralReport
    fields = ("reporter_email", "category", "subject", "content")
    template_name = "dictionary/reporting/general.html"

    def get_success_url(self):
        notifications.info(self.request, "bir kenara yazdık bunu. inceleyeceğiz.")
        return reverse("home")

    def form_invalid(self, form):
        notifications.error(self.request, "iletişim formu gönderilemedi.")
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method not in ('POST', 'PUT'):
            referrer_entry = self.request.GET.get("referrer_entry")
            referrer_topic = self.request.GET.get("referrer_topic")
            if referrer_entry and referrer_topic:
                template = f'"{referrer_topic}" başlığındaki #{referrer_entry} numaralı entry hakkında'
                kwargs.update({"data": {"subject": template}})
        return kwargs
