from django.contrib import admin

from ..models import Entry, Comment


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    search_fields = ("pk",)
    autocomplete_fields = ("topic", "author")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    autocomplete_fields = ("entry", "author")
    fields = ("author", "entry", "content")
    list_display = ("author", "entry", "id")

    def has_change_permission(self, request, obj=None):
        return False
