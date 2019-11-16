from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from .models import Author, Entry, Message
from django.forms.widgets import SelectDateWidget

# Any changes made in models.py regarding choicefields should also be made here.

GENDERS = (('NO', 'Boşver'), ('MN', 'Erkek'), ('WM', 'Kadın'), ('OT', 'Diğer'))


class LoginForm(AuthenticationForm):
    error_messages = {'invalid_login': (
        "giriş yapılamadı. doğru e-posta ve parola kombinasyonunu girdiğinizden emin olun. bilgileriniz büyük-küçük "
        "harf hassastır. e-posta adresinizi onayladığınzdan emin olun.")}
    remember_me = forms.BooleanField(required=False, label="beni hatırla")


class PreferencesForm(UserChangeForm):
    password = None
    ENTRY_COUNTS = ((10, "10"), (30, "30"), (50, "50"), (100, "100"))
    MESSAGE_PREFERENCE = (
        ("DS", "hiçkimse"), ("AU", "yazar ve çaylaklar"), ("AO", "yazarlar"), ("FO", "takip ettiklerim"))

    gender = forms.ChoiceField(choices=GENDERS, label="cinsiyet")
    birth_date = forms.DateField(widget=SelectDateWidget(years=range(1910, 2000)), label="doğum günü")
    entries_per_page = forms.ChoiceField(choices=ENTRY_COUNTS, label="sayfa başına gösterilecek entry sayısı")
    message_preference = forms.ChoiceField(choices=MESSAGE_PREFERENCE, label="mesaj")

    class Meta:
        model = Author
        fields = ("gender", "birth_date", "entries_per_page", "message_preference")


class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=254,
                             help_text='Gerekli. Kayıt işlemini tamamlamak için geçerli bir mail adresi girin.',
                             label="e-mail adresi")
    gender = forms.ChoiceField(choices=GENDERS, label="cinsiyet")
    birth_date = forms.DateField(help_text='Gerekli.', widget=SelectDateWidget(years=range(1910, 2000)),
                                 label="doğum günü")
    terms_conditions = forms.BooleanField(required=True)

    class Meta:
        model = Author
        fields = ('username', 'email', 'password1', 'password2',)
        labels = {'username': "takma isim"}


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ('content', 'is_draft')


class SendMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('body',)


class ChangeEmailForm(forms.Form):
    email1 = forms.EmailField(max_length=254, label="yeni e-posta adresi")
    email2 = forms.EmailField(max_length=254, label="yeni e-posta adresi (tekrar)")
    password_confirm = forms.CharField(label="parolanızı teyit edin", strip=False, widget=forms.PasswordInput)

    def clean(self):
        form_data = self.cleaned_data
        if form_data["email1"] != form_data["email2"]:
            raise forms.ValidationError("e-postalar uyuşmadı")
        else:
            if Author.objects.filter(email=form_data["email1"]).exists():
                # todo: if multiple unactivated accounts exist, delete rest when one of them is activated
                raise forms.ValidationError("bu e-posta kullanımda")

        super().clean()
