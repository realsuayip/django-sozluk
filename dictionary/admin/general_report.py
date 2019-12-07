from . import admin


class GeneralReportAdmin(admin.ModelAdmin):
    list_display = ("subject", "reporter_email", "is_open",)
    readonly_fields = ('reporter_email', 'category', 'subject', 'content')

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-is_open")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
