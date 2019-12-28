from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.forms.widgets import SelectDateWidget

from ..models import Author, Entry, Message, Memento


class PreferencesForm(UserChangeForm):
    password = None

    gender = forms.ChoiceField(choices=Author.GENDERS, label="cinsiyet")
    birth_date = forms.DateField(widget=SelectDateWidget(years=range(2000, 1900, -1)), label="doğum günü")
    entries_per_page = forms.ChoiceField(choices=Author.ENTRY_COUNTS, label="sayfa başına gösterilecek entry sayısı")
    topics_per_page = forms.ChoiceField(choices=Author.TOPIC_COUNTS, label="sayfa başına gösterilecek başlık sayısı")
    message_preference = forms.ChoiceField(choices=Author.MESSAGE_PREFERENCE, label="mesaj")

    class Meta:
        model = Author
        fields = ("gender", "birth_date", "entries_per_page", "topics_per_page", "message_preference")


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ('content', 'is_draft')


class SendMessageForm(forms.ModelForm):
    # Used in conversation (previously created)
    class Meta:
        model = Message
        fields = ('body',)
        labels = {"body": "mesajınız"}

    def clean(self):
        if len(self.cleaned_data.get("body")) < 3:
            raise forms.ValidationError("bu mesaj çok kısa be koçum")

        super().clean()


class StandaloneMessageForm(SendMessageForm):
    # Used to create new conversations (in messages list view)
    recipient = forms.CharField(label="kime")


class MementoForm(forms.ModelForm):
    class Meta:
        model = Memento
        fields = ("body",)
