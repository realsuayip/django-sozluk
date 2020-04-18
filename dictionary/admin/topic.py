from django.contrib import admin
from django.urls import path

from ..admin.views.topic import TopicMove
from ..models import Topic
from ..utils.admin import IntermediateActionHandler


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("title", "category", "mirrors")}),
        ("Erişilebilirlik seçenekleri", {"fields": ("is_pinned", "is_banned", "is_censored")}),
        ("Üstveri", {"fields": ("created_by", "date_created")}),
    )

    list_display = ("title", "created_by", "is_censored", "is_banned", "date_created")
    list_filter = ("category", "is_pinned", "is_censored", "is_banned")
    search_fields = ("title",)
    autocomplete_fields = ("category", "mirrors")
    actions = ("move_topic",)

    def get_readonly_fields(self, request, obj=None):
        readonly = ("created_by", "date_created")
        return readonly + ("title",) if obj else readonly

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [path("actions/move/", self.admin_site.admin_view(TopicMove.as_view()), name="topic-move")]
        return custom_urls + urls

    # Custom permissions for action | pylint: disable=R0201
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
