from django.contrib import admin
from ..models import Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    search_fields = ("pk",)
    autocomplete_fields = ("topic", "author")
