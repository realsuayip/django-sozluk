from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.forms.widgets import SelectDateWidget

from ..models import Author, Entry, Message, Memento


class PreferencesForm(UserChangeForm):
    password = None

    gender = forms.ChoiceField(choices=Author.GENDERS, label="cinsiyet")
    birth_date = forms.DateField(widget=SelectDateWidget(years=range(1910, 2000)), label="doğum günü")
    entries_per_page = forms.ChoiceField(choices=Author.ENTRY_COUNTS, label="sayfa başına gösterilecek entry sayısı")
    message_preference = forms.ChoiceField(choices=Author.MESSAGE_PREFERENCE, label="mesaj")

    class Meta:
        model = Author
        fields = ("gender", "birth_date", "entries_per_page", "message_preference")


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ('content', 'is_draft')


class SendMessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ('body',)


class MementoForm(forms.ModelForm):
    class Meta:
        model = Memento
        fields = ("body",)
