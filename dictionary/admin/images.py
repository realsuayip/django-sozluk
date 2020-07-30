from django.contrib import admin

from ..models import Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    search_fields = ("slug", "author__username", "file")
    list_display = ("slug", "author",  "date_created", "file", "is_deleted")

    def get_actions(self, request):
        return []

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
