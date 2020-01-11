from django.contrib import admin
from django.shortcuts import reverse, redirect
from django.urls import path

from ..admin.views.topic import TopicMove
from ..models import Topic


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "date_created")
    search_fields = ["title"]
    autocomplete_fields = ("category",)
    readonly_fields = ("created_by", "date_created")

    actions = ["move_topic"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [path("actions/move/", self.admin_site.admin_view(TopicMove.as_view()), name="topic-move")]
        return custom_urls + urls

    def move_topic(self, request, queryset):
        source_list = '-'.join([str(value["id"]) for value in queryset.values("id")])
        return redirect(reverse("admin:topic-move") + f"?source_list={source_list}")

    move_topic.short_description = "Seçili başlıklardaki entry'leri taşı"
