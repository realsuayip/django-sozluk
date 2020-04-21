from smtplib import SMTPException

from django.contrib import messages as notifications
from django.core.mail import EmailMessage
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, View

from ..models import GeneralReport
from ..utils import time_threshold
from ..utils.email import DOMAIN, FROM_EMAIL, PROTOCOL


class GeneralReportView(CreateView):
    model = GeneralReport
    fields = ("reporter_email", "category", "subject", "content")
    template_name = "dictionary/reporting/general.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        instance = form.save(commit=False)
        key = instance.key
        link = f"{PROTOCOL}://{DOMAIN}{reverse_lazy('verify-report', kwargs={'key': key})}"
        body = f"""<p>iletişim formunun tarafımıza ulaşması için aşağıdaki bağlantıyı takip etmeniz
                    gerekiyor. eğer 'iletişim formu falan göndermedim ben, ne oluyor be?' diyorsanız, hiçbir
                    şey olmamış gibi hayatınıza devam edebilirsiniz. bağlantı:</p><a href="{link}">{link}</a>"""

        try:
            email = EmailMessage("iletişim formu için onay", body, FROM_EMAIL, [instance.reporter_email])
            email.content_subtype = "html"
            email.send()
            notifications.info(
                self.request,
                "e-posta adresinize bir onaylama bağlantısı gönderildi."
                " bu bağlantıya tıkladıktan sonra isteğiniz bize ulaşacak.",
                extra_tags="persistent",
            )
        except SMTPException:
            return super().form_invalid(form)

        return super().form_valid(form)

    def form_invalid(self, form):
        notifications.error(
            self.request, "iletişim formu gönderilemedi. daha sonra tekrar deneyin.", extra_tags="persistent"
        )
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method not in ("POST", "PUT"):
            referrer_entry = self.request.GET.get("referrer_entry")
            referrer_topic = self.request.GET.get("referrer_topic")
            if referrer_entry and referrer_topic:
                template = f'"{referrer_topic}" başlığındaki #{referrer_entry} numaralı entry hakkında'
                kwargs.update({"data": {"subject": template}})
        return kwargs


class VerifyReport(View):
    def get(self, *args, **kwargs):
        key = kwargs.get("key")
        report = GeneralReport.objects.filter(
            is_verified=False, date_created__gte=time_threshold(hours=24), key=key
        ).first()

        if report is not None:
            report.is_verified = True
            report.date_verified = timezone.now()
            report.save()
            notifications.success(self.request, "iletişim talebiniz başarıyla iletildi.", extra_tags="persistent")
        else:
            notifications.error(
                self.request,
                "ne yazık ki iletişim talebiniz iletilemedi. onaylama bağlantısı geçersiz."
                " lütfen bağlantı adresini kontrol edin."
                " <strong>onaylama bağlantısı gönderimden itibaren bir gün için geçerlidir.</strong>",
                extra_tags="persistent",
            )
        return redirect(reverse("home"))
