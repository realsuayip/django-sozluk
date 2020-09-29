from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.forms.widgets import SelectDateWidget
from django.utils.translation import gettext, gettext_lazy as _

from dictionary.models import Author, Entry, Memento, Message


class PreferencesForm(UserChangeForm):
    password = None

    gender = forms.ChoiceField(choices=Author.Gender.choices, label=_("gender"))
    birth_date = forms.DateField(widget=SelectDateWidget(years=range(2000, 1900, -1)), label=_("birth date"))
    entries_per_page = forms.ChoiceField(choices=Author.EntryCount.choices, label=_("entries per page"))
    topics_per_page = forms.ChoiceField(choices=Author.TopicCount.choices, label=_("topics per page"))
    message_preference = forms.ChoiceField(choices=Author.MessagePref.choices, label=_("message preference"))
    allow_receipts = forms.BooleanField(required=False, label=_("show read receipts"))
    allow_uncategorized = forms.BooleanField(required=False, label=_("allow uncategorized topics in today"))
    allow_site_announcements = forms.BooleanField(required=False, label=_("include site announcements in my activity"))

    class Meta:
        model = Author
        fields = (
            "gender",
            "birth_date",
            "entries_per_page",
            "topics_per_page",
            "message_preference",
            "allow_receipts",
            "allow_uncategorized",
            "allow_site_announcements",
        )


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ("content",)
        error_messages = {"content": {"required": _("my dear, just write your entry, how hard could it be?")}}


class SendMessageForm(forms.ModelForm):
    # Used in conversation (previously created)
    class Meta:
        model = Message
        fields = ("body",)
        labels = {"body": _("message")}

        error_messages = {"body": {"required": _("can't really understand you")}}

    def clean(self):
        msg = self.cleaned_data.get("body", "")

        if len(msg) < 3:
            raise forms.ValidationError(gettext("that message is just too short"))

        super().clean()


class StandaloneMessageForm(SendMessageForm):
    # Used to create new conversations (in messages list view)
    recipient = forms.CharField(label=_("to who"))


class MementoForm(forms.ModelForm):
    class Meta:
        model = Memento
        fields = ("body",)
