from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.utils.translation import gettext_lazy as _

from dictionary.models import Entry, Comment


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    search_fields = ("id",)
    autocomplete_fields = ("topic", "author")
    list_display = ("id", "topic", "author")
    list_filter = (("date_created", DateFieldListFilter),)
    ordering = ("-date_created",)
    fieldsets = (
        (None, {"fields": ("author", "topic", "content", "vote_rate")}),
        (_("Metadata"), {"fields": ("is_draft", "date_created", "date_edited")}),
    )

    readonly_fields = ("author", "content", "vote_rate", "is_draft", "date_created", "date_edited")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    autocomplete_fields = ("entry", "author")
    fields = ("author", "entry", "content")
    list_display = ("author", "entry", "id")
    ordering = ("-date_created",)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
