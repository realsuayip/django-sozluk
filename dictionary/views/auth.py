from contextlib import suppress
from smtplib import SMTPException

from django.contrib import messages as notifications
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.views.generic import View
from django.views.generic.edit import FormView

from ..forms.auth import ChangeEmailForm, LoginForm, ResendEmailForm, SignUpForm, TerminateAccountForm
from ..models import AccountTerminationQueue, Author, PairedSession, UserVerification
from ..utils import time_threshold
from ..utils.email import FROM_EMAIL, send_email_confirmation
from ..utils.mixins import PasswordConfirmMixin
from ..utils.settings import PASSWORD_CHANGED_MESSAGE, TERMINATION_ONHOLD_MESSAGE


class Login(LoginView):
    form_class = LoginForm
    template_name = "dictionary/registration/login.html"

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me", False)

        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 weeks
        else:
            self.request.session.set_expiry(7200)

        # Check if the user cancels account termination.
        with suppress(AccountTerminationQueue.DoesNotExist):
            AccountTerminationQueue.objects.get(author=form.get_user()).delete()
            notifications.info(self.request, "tekrar hoşgeldiniz. hesabınız aktif oldu.")

        notifications.info(self.request, "başarıyla giriş yaptınız efendim")
        return super().form_valid(form)


class Logout(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            success_message = "başarıyla çıkış yaptınız efendim"
            notifications.info(self.request, success_message)
        return super().dispatch(request)


class SignUp(FormView):
    form_class = SignUpForm
    template_name = "dictionary/registration/signup.html"

    def form_valid(self, form):
        user = form.save(commit=False)
        user.username = form.cleaned_data.get("username").lower()
        user.birth_date = form.cleaned_data.get("birth_date")
        user.gender = form.cleaned_data.get("gender")
        user.save()
        send_email_confirmation(user, user.email)
        notifications.info(
            self.request,
            "e-posta adresinize bir onay bağlantısı gönderildi."
            " bu bağlantıya tıklayarak hesabınızı aktif hale getirip"
            " giriş yapabilirsiniz.",
        )
        return redirect("login")


class ConfirmEmail(View):
    success = False
    template_name = "dictionary/registration/email/confirmation_result.html"

    def get(self, request, uidb64, token):
        try:
            user_id = urlsafe_base64_decode(uidb64).decode()
            verification_object = UserVerification.objects.get(
                author_id=user_id, expiration_date__gte=time_threshold(hours=24)
            )
        except (ValueError, UnicodeDecodeError, UserVerification.DoesNotExist):
            return self.render_to_response()

        if check_password(token, verification_object.verification_token):
            author = Author.objects.get(id=user_id)

            if not author.is_active:
                author.is_active = True
                author.save()
            else:
                author.email = verification_object.new_email
                author.save()

            self.success = True
            UserVerification.objects.filter(author=author).delete()

        return self.render_to_response()

    def render_to_response(self):
        return render(self.request, self.template_name, context={"success": self.success})


class ResendEmailConfirmation(FormView):
    form_class = ResendEmailForm
    template_name = "dictionary/registration/email/resend_form.html"

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        author = Author.objects.get(email=email)
        send_email_confirmation(author, email)
        notifications.info(self.request, "onaylama bağlantısını içeren e-posta gönderildi")
        return redirect("login")


class ChangePassword(LoginRequiredMixin, PasswordChangeView):
    success_url = reverse_lazy("user_preferences")
    template_name = "dictionary/user/preferences/password.html"

    def form_valid(self, form):
        message = PASSWORD_CHANGED_MESSAGE.format(self.request.user.username)

        # Send a 'your password has been changed' message to ensure security.
        try:
            self.request.user.email_user("parolanız değişti", message, FROM_EMAIL)
        except SMTPException:
            notifications.error(self.request, "parolanızı değiştiremedik. daha sonra tekrar deneyin.")
            return super().form_invalid(form)

        notifications.info(self.request, "işlem tamam")
        return super().form_valid(form)


class ChangeEmail(LoginRequiredMixin, PasswordConfirmMixin, FormView):
    template_name = "dictionary/user/preferences/email.html"
    form_class = ChangeEmailForm
    success_url = reverse_lazy("user_preferences")

    def form_valid(self, form):
        send_email_confirmation(self.request.user, form.cleaned_data.get("email1"))
        notifications.info(self.request, "e-posta onayından sonra adresiniz değişecektir.")
        return redirect(self.success_url)


class TerminateAccount(LoginRequiredMixin, PasswordConfirmMixin, FormView):
    template_name = "dictionary/user/preferences/terminate.html"
    form_class = TerminateAccountForm
    success_url = reverse_lazy("login")

    def form_valid(self, form):
        message = TERMINATION_ONHOLD_MESSAGE.format(self.request.user.username)

        # Send a message to ensure security.
        try:
            self.request.user.email_user("hesabınız donduruldu", message, FROM_EMAIL)
        except SMTPException:
            notifications.error(self.request, "işlem gerçekleştirilemedi. daha sonra tekrar deneyin.")
            return super().form_invalid(form)

        termination_choice = form.cleaned_data.get("state")
        AccountTerminationQueue.objects.create(author=self.request.user, state=termination_choice)
        # Unlike logout(), this invalidates ALL sessions across devices.
        PairedSession.objects.filter(user=self.request.user).delete()
        notifications.info(self.request, "isteğinizi aldık. görüşmek üzere")
        return super().form_valid(form)
