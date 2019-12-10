from . import admin
from ..models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    exclude = ("slug",)
