from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.forms.widgets import SelectDateWidget
from django.utils.translation import gettext as _, gettext_lazy as _lazy

from ..models import Author, AccountTerminationQueue


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": (
            _lazy(
                "could not log in. make sure that you entered correct"
                " combination of e-mail and password. your credentials are"
                " case sensitive. make sure that you confirmed your e-mail."
            )
        )
    }
    remember_me = forms.BooleanField(required=False, label=_lazy("remember me"))


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        help_text=_lazy("required. in order to complete registration, provide a valid e-mail address."),
        label=_lazy("e-mail"),
    )
    gender = forms.ChoiceField(choices=Author.GENDERS, label=_lazy("gender"))
    birth_date = forms.DateField(widget=SelectDateWidget(years=range(2000, 1900, -1)), label=_lazy("birth date"))
    terms_conditions = forms.BooleanField(required=True)

    class Meta:
        model = Author
        fields = (
            "username",
            "email",
            "password1",
            "password2",
        )
        labels = {"username": _lazy("nickname")}


class ResendEmailForm(forms.Form):
    email = forms.EmailField(max_length=254, label=_lazy("the e-mail address you used to register your account"))

    def clean(self):
        if not self.errors:
            try:
                author = Author.objects.get(email=self.cleaned_data.get("email"))
                if author.is_active:
                    raise forms.ValidationError(_("this e-mail has already been confirmed."))
            except Author.DoesNotExist:
                raise forms.ValidationError(_("no such e-mail, never heard of it."))

        super().clean()


class ChangeEmailForm(forms.Form):
    email1 = forms.EmailField(max_length=254, label=_lazy("new e-mail address"))
    email2 = forms.EmailField(max_length=254, label=_lazy("new e-mail address (again)"))
    password_confirm = forms.CharField(label=_lazy("confirm your password"), strip=False, widget=forms.PasswordInput)

    def clean(self):
        form_data = self.cleaned_data

        if form_data.get("email1") != form_data.get("email2"):
            raise forms.ValidationError(_("e-mails didn't match."))

        if Author.objects.filter(email=form_data.get("email1")).exists():
            raise forms.ValidationError(_("this e-mail is already in use."))

        super().clean()


class TerminateAccountForm(forms.ModelForm):
    password_confirm = forms.CharField(label=_lazy("confirm your password"), strip=False, widget=forms.PasswordInput)

    class Meta:
        model = AccountTerminationQueue
        fields = ("state",)
