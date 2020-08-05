from django.contrib import admin

from ..models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "weight", "description", "is_default", "is_pseudo")
    exclude = ("slug",)
