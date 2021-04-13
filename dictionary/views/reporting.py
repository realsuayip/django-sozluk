from smtplib import SMTPException

from django.contrib import messages as notifications
from django.core.mail import EmailMessage
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, View

from dictionary.conf import settings
from dictionary.models import GeneralReport
from dictionary.utils import time_threshold


class GeneralReportView(CreateView):
    model = GeneralReport
    fields = ("reporter_email", "category", "subject", "content")
    template_name = "dictionary/reporting/general.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        instance = form.save(commit=False)

        if self.request.user.is_authenticated:
            instance.reporter_email = self.request.user.email
            instance.is_verified = True

        if GeneralReport.objects.filter(
            reporter_email=instance.reporter_email, date_created__gte=time_threshold(minutes=15)
        ).exists():
            notifications.error(
                self.request, _("it hasn't been long since you last sent a report."), extra_tags="persistent"
            )
            return self.form_invalid(form)

        # User is already logged in, no verification required.
        if self.request.user.is_authenticated:
            notifications.success(
                self.request, _("your report request has been successfully sent."), extra_tags="persistent"
            )
            return super().form_valid(form)

        # Prepare and send a verification email.
        key = instance.key
        link = f"{settings.PROTOCOL}://{settings.DOMAIN}{reverse('verify-report', kwargs={'key': key})}"

        message = _(
            "in order reporting form to reach us, you need to follow the link given below."
            " if you are in mindset such as 'what the hell? i did not send such report', you"
            " can continue with your life as if nothing ever happened. the link:"
        )

        body = f'<p>{message}</p><a href="{link}">{link}</a>'

        try:
            email = EmailMessage(_("confirmation of reporting"), body, settings.FROM_EMAIL, [instance.reporter_email])
            email.content_subtype = "html"
            email.send()
            notifications.info(
                self.request,
                _(
                    "a confirmation link has been sent to your e-mail address."
                    " your report will reach us if you follow the given link."
                ),
                extra_tags="persistent",
            )
        except (SMTPException, ConnectionRefusedError):
            return self.form_invalid(form)

        return super().form_valid(form)

    def form_invalid(self, form):
        notifications.error(
            self.request, _("we couldn't handle your request. try again later."), extra_tags="persistent"
        )
        return super().form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        if self.request.method not in ("POST", "PUT"):
            data = {}
            referrer_entry, referrer_topic = (
                self.request.GET.get("referrer_entry"),
                self.request.GET.get("referrer_topic"),
            )

            if referrer_entry and referrer_topic:
                data["subject"] = _(
                    "about the entry (#%(referrer_entry)s), in the topic titled '%(referrer_topic)s'"
                ) % {"referrer_entry": referrer_entry, "referrer_topic": referrer_topic}

            if self.request.user.is_authenticated:
                data["reporter_email"] = self.request.user.email

            kwargs.update({"data": data})

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
            notifications.success(
                self.request, _("your report request was successfully sent."), extra_tags="persistent"
            )
        else:
            notifications.error(
                self.request,
                _(
                    "unfortunately your report request was not sent. the confirmation link is invalid;"
                    " please check the confirmation link. <strong>confirmation link is only valid for"
                    " 24 hours after it was sent.</strong>"
                ),
                extra_tags="persistent",
            )
        return redirect(reverse("home"))
