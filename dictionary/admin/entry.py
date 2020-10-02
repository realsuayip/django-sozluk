from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.utils.translation import gettext_lazy as _

from dictionary.models import Entry, Comment


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    search_fields = ("id", "author__username", "topic__title")
    autocomplete_fields = ("topic",)
    list_display = ("id", "topic", "author", "vote_rate")
    list_filter = (
        ("date_created", DateFieldListFilter),
        ("date_edited", DateFieldListFilter),
        "is_draft",
        "author__is_novice",
        "topic__category",
    )
    ordering = ("-date_created",)
    fieldsets = (
        (None, {"fields": ("author", "topic", "content", "vote_rate")}),
        (_("Metadata"), {"fields": ("is_draft", "date_created", "date_edited")}),
    )

    readonly_fields = ("author", "content", "vote_rate", "is_draft", "date_created", "date_edited")

    def has_add_permission(self, request, obj=None):
        return False


def topic_title(obj):
    return obj.entry.topic.title


def entry_content(obj):
    return obj.entry.content


topic_title.short_description = _("Topic")
entry_content.short_description = _("Entry")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    autocomplete_fields = ("entry", "author")
    search_fields = ("author__username", "id")
    fields = ("author", topic_title, entry_content, "content")
    list_display = ("author", topic_title, "id", "date_created")
    list_filter = (
        ("date_created", DateFieldListFilter),
        ("date_edited", DateFieldListFilter),
    )
    ordering = ("-date_created",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
