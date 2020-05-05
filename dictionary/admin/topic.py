from django.contrib import admin
from django.urls import path

from ..admin.views.topic import TopicMove
from ..models import Topic
from ..utils.admin import intermediate


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("title", "category", "mirrors")}),
        ("Erişilebilirlik seçenekleri", {"fields": ("is_pinned", "is_banned", "is_censored")}),
        ("Üstveri", {"fields": ("created_by", "date_created")}),
        (
            "Medya",
            {
                "classes": ("collapse",),
                "fields": ("media",),
                "description": "<br>Sosyal medya sitelerindeki içerikleri başlığa gömebilirsiniz."
                " Gömmek istediğiniz içeriğin adreslerini satır satır girmelisiniz."
                " Mevcut seçenekler ve örnek adresler:<br><br>"
                "<b>YouTube videosu: </b>(https://www.youtube.com/embed/qXN15uh4DLU)<br>"
                "<b>Instagram gönderisi: </b>(https://www.instagram.com/p/B4nfnuRg0sp/)<br>"
                "<b>Spotify şarkısı: </b>(https://open.spotify.com/embed/track/1idpc4Pr94WH9GYU5umNfz)<br>"
                "<b>Spotify albümü: </b>(https://open.spotify.com/embed/album/1yGbNOtRIgdIiGHOEBaZWf)<br>"
                "<b>Spotify çalma listesi: </b>"
                "(https://open.spotify.com/embed/user/spotify/playlist/37i9dQZF1DX1tz6EDao8it)<br>",
            },
        ),
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
    @intermediate
    def move_topic(self, request, queryset):
        return "admin:topic-move"

    # Short descriptions
    move_topic.short_description = "Seçili başlıklardaki entry'leri taşı"

    # Permissions
    move_topic.allowed_permissions = ["move_topic"]
