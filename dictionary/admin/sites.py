from django.conf import settings
from django.contrib import admin
from django.urls import path

from dictionary.admin.views.sites import ClearCache


class SiteAdmin(admin.ModelAdmin):
    fields = ("id", "name", "domain")
    readonly_fields = ("id",)
    list_display = ("id", "name", "domain")
    list_display_links = ("name",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("cache/", self.admin_site.admin_view(ClearCache.as_view()), name="clear-cache"),
        ]
        return custom_urls + urls

    def has_delete_permission(self, request, obj=None):
        if obj and obj.id == settings.SITE_ID:
            return False

        return super().has_delete_permission(request, obj)
