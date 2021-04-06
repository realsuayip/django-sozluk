from django.contrib import admin
from django.contrib.admin import DateFieldListFilter

from dictionary.models import Category, Suggestion


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_editable = ("weight",)
    list_display = ("name", "weight", "description", "is_default", "is_pseudo")
    exclude = ("slug",)


@admin.register(Suggestion)
class SuggestionAdmin(admin.ModelAdmin):
    search_fields = ("author__username", "topic__title")
    list_display = ("author", "topic", "category", "direction", "date_created")
    list_filter = (
        "direction",
        "category",
        ("date_created", DateFieldListFilter),
    )

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
