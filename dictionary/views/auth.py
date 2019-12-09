from django.contrib import messages as notifications
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import render, redirect
from django.views.generic import View
from django.views.generic.edit import FormView
from django.urls import reverse, reverse_lazy
from django.utils.http import urlsafe_base64_decode

from ..forms.auth import SignUpForm, LoginForm, ChangeEmailForm, ResendEmailForm
from ..models import UserVerification, Author
from ..utils.email import send_email_confirmation
from ..utils.settings import TIME_THRESHOLD_24H


class Login(LoginView):
    form_class = LoginForm
    template_name = "dictionary/registration/login.html"

    def form_valid(self, form):
        remember_me = form.cleaned_data.get("remember_me", False)
        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 weeks
        else:
            self.request.session.set_expiry(7200)

        success_message = "başarıyla giriş yaptınız efendim"
        notifications.info(self.request, success_message)
        return super().form_valid(form)


class Logout(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            success_message = "başarıyla çıkış yaptınız efendim"
            notifications.info(self.request, success_message)
        return super().dispatch(request)


class SignUp(FormView):
    form_class = SignUpForm
    template_name = 'dictionary/registration/signup.html'

    def form_valid(self, form):
        user = form.save(commit=False)
        user.username = form.cleaned_data.get('username').lower()
        user.birth_date = form.cleaned_data.get('birth_date')
        user.gender = form.cleaned_data.get('gender')
        user.save()
        send_email_confirmation(user, user.email)
        notifications.info(self.request, "e-posta adresinize bir onay bağlantısı gönderildi."
                                         "bu bağlantıya tıklayarak hesabınızı aktif hale getirip giriş yapabilirsiniz.")
        return redirect('login')


class ConfirmEmail(View):
    success = False

    def get(self, request, uidb64, token):
        try:
            user_id = urlsafe_base64_decode(uidb64).decode()
            verification_object = UserVerification.objects.get(author_id=user_id,
                                                               expiration_date__gte=TIME_THRESHOLD_24H)
        except (ValueError, UnicodeDecodeError, UserVerification.DoesNotExist):
            return self.response()

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

        return self.response()

    def response(self):
        return render(self.request, "dictionary/registration/email/confirmation_result.html",
                      context={"success": self.success})


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
        notifications.info(self.request, "işlem tamam")
        return super().form_valid(form)


class ChangeEmail(LoginRequiredMixin, FormView):
    template_name = "dictionary/user/preferences/email.html"
    form_class = ChangeEmailForm
    success_url = reverse_lazy("user_preferences")

    def form_valid(self, form):
        if not self.request.user.check_password(form.cleaned_data.get("password_confirm")):
            notifications.error(self.request, "parolanızı yanlış girdiniz")
            return redirect(reverse("user_preferences_email"))

        send_email_confirmation(self.request.user, form.cleaned_data.get("email1"))
        notifications.info(self.request, "e-posta onayından sonra adresiniz değişecektir.")
        return redirect(self.success_url)
