from django.contrib import admin
from django.contrib.admin import DateFieldListFilter

from dictionary.models import Image


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    search_fields = ("slug", "author__username", "file")
    list_display = ("slug", "author", "date_created", "file", "is_deleted")
    list_filter = (("date_created", DateFieldListFilter), "is_deleted")
    ordering = ("-date_created",)
    readonly_fields = ("author", "file", "date_created")
    list_editable = ("is_deleted",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related("author")

    def has_add_permission(self, request, obj=None):
        return False
