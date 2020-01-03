from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.forms.widgets import SelectDateWidget

from ..models import Author


class LoginForm(AuthenticationForm):
    error_messages = {'invalid_login': (
        "giriş yapılamadı. doğru e-posta ve parola kombinasyonunu girdiğinizden emin olun. bilgileriniz büyük-küçük "
        "harf hassastır. e-posta adresinizi onayladığınzdan emin olun.")}
    remember_me = forms.BooleanField(required=False, label="beni hatırla")


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254,
                             help_text='Gerekli. Kayıt işlemini tamamlamak için geçerli bir mail adresi girin.',
                             label="e-mail adresi")
    gender = forms.ChoiceField(choices=Author.GENDERS, label="cinsiyet")
    birth_date = forms.DateField(help_text='Gerekli.', widget=SelectDateWidget(years=range(2000, 1900, -1)),
                                 label="doğum günü")
    terms_conditions = forms.BooleanField(required=True)

    class Meta:
        model = Author
        fields = ('username', 'email', 'password1', 'password2',)
        labels = {'username': "takma isim"}


class ResendEmailForm(forms.Form):
    email = forms.EmailField(max_length=254, label="kayıt olurken kullandığınız e-posta adresiniz")

    def clean(self):
        if not self.errors:
            try:
                author = Author.objects.get(email=self.cleaned_data.get('email'))
                if author.is_active:
                    raise forms.ValidationError("bu e-posta çoktan onaylanmış")
            except Author.DoesNotExist:
                raise forms.ValidationError("böyle bir e-posta yok yalnız, hiç duymadım.")

        super().clean()


class ChangeEmailForm(forms.Form):
    email1 = forms.EmailField(max_length=254, label="yeni e-posta adresi")
    email2 = forms.EmailField(max_length=254, label="yeni e-posta adresi (tekrar)")
    password_confirm = forms.CharField(label="parolanızı teyit edin", strip=False, widget=forms.PasswordInput)

    def clean(self):
        form_data = self.cleaned_data
        if form_data["email1"] != form_data["email2"]:
            raise forms.ValidationError("e-postalar uyuşmadı")

        if Author.objects.filter(email=form_data["email1"]).exists():
            raise forms.ValidationError("bu e-posta kullanımda")

        super().clean()
