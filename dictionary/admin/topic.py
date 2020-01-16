from django.contrib import admin
from django.urls import path

from ..admin.views.topic import TopicMove
from ..models import Topic
from ..utils.admin import IntermediateActionHandler


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

    # Custom permissions for action
    def has_move_topic_permission(self, request):
        """Does the user have the move_topic permission?"""
        return request.user.has_perm("dictionary.move_topic")

    # Actions
    def move_topic(self, request, queryset):
        action = IntermediateActionHandler(queryset, "admin:topic-move")
        return action.redirect_url

    # Short descriptions
    move_topic.short_description = "Seçili başlıklardaki entry'leri taşı"

    # Permissions
    move_topic.allowed_permissions = ["move_topic"]
