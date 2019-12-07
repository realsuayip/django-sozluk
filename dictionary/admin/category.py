from . import admin


class CategoryAdmin(admin.ModelAdmin):
    exclude = ("slug",)
