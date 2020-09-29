from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.forms.widgets import SelectDateWidget
from django.utils.translation import gettext, gettext_lazy as _

from dictionary.models import Author, AccountTerminationQueue


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": (
            _(
                "could not log in. make sure that you entered correct"
                " combination of e-mail and password. your credentials are"
                " case sensitive. make sure that you confirmed your e-mail."
            )
        )
    }
    remember_me = forms.BooleanField(required=False, label=_("remember me"))


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        max_length=254,
        help_text=_("required. in order to complete registration, provide a valid e-mail address."),
        label=_("e-mail"),
    )
    gender = forms.ChoiceField(choices=Author.Gender.choices, label=_("gender"))
    birth_date = forms.DateField(widget=SelectDateWidget(years=range(2000, 1900, -1)), label=_("birth date"))
    terms_conditions = forms.BooleanField(required=True)

    class Meta:
        model = Author
        fields = (
            "username",
            "email",
            "password1",
            "password2",
        )
        labels = {"username": _("nickname")}


class ResendEmailForm(forms.Form):
    email = forms.EmailField(max_length=254, label=_("the e-mail address you used to register your account"))

    def clean(self):
        if not self.errors:
            try:
                author = Author.objects.get(email=self.cleaned_data.get("email"))
                if author.is_active:
                    raise forms.ValidationError(gettext("this e-mail has already been confirmed."))
            except Author.DoesNotExist as exc:
                raise forms.ValidationError(gettext("no such e-mail, never heard of it.")) from exc

        super().clean()


class ChangeEmailForm(forms.Form):
    email1 = forms.EmailField(max_length=254, label=_("new e-mail address"))
    email2 = forms.EmailField(max_length=254, label=_("new e-mail address (again)"))
    password_confirm = forms.CharField(label=_("confirm your password"), strip=False, widget=forms.PasswordInput)

    def clean(self):
        form_data = self.cleaned_data

        if form_data.get("email1") != form_data.get("email2"):
            raise forms.ValidationError(gettext("e-mails didn't match."))

        if Author.objects.filter(email=form_data.get("email1")).exists():
            raise forms.ValidationError(gettext("this e-mail is already in use."))

        super().clean()


class TerminateAccountForm(forms.ModelForm):
    password_confirm = forms.CharField(label=_("confirm your password"), strip=False, widget=forms.PasswordInput)

    class Meta:
        model = AccountTerminationQueue
        fields = ("state",)
