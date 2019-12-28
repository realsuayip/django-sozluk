from django.contrib import admin
from ..models import Topic


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "date_created")
    search_fields = ["title"]
    autocomplete_fields = ("category", )
    readonly_fields = ("created_by", "date_created")
