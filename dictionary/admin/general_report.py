from django.contrib import admin, messages as notifications
from django.contrib.admin import DateFieldListFilter
from django.utils.translation import gettext, gettext_lazy as _

from dictionary.models import GeneralReport


@admin.register(GeneralReport)
class GeneralReportAdmin(admin.ModelAdmin):
    search_fields = ("subject", "reporter_email")
    list_display = ("subject", "reporter_email", "category", "date_created", "is_open")
    readonly_fields = (
        "reporter_email",
        "category",
        "subject",
        "content",
        "date_created",
        "date_verified",
        "is_verified",
    )
    fieldsets = (
        (_("Report content"), {"fields": ("category", "subject", "content")}),
        (_("Metadata"), {"fields": ("reporter_email", "date_created", "is_verified", "date_verified")}),
        (_("Evaluation"), {"fields": ("is_open",)}),
    )
    list_per_page = 30
    list_filter = ("category", "is_open", ("date_created", DateFieldListFilter))
    list_editable = ("is_open",)
    ordering = ("-is_open",)
    actions = ("close_report", "open_report")

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(is_verified=False)

    def close_report(self, request, queryset):
        queryset.update(is_open=False)
        notifications.success(request, gettext("Selected reports' status were marked as closed."))

    def open_report(self, request, queryset):
        queryset.update(is_open=True)
        notifications.success(request, gettext("Selected reports' status were marked as open."))

    close_report.short_description = _("Mark selected reports' status as closed.")
    open_report.short_description = _("Mark selected reports' status as open.")

    def has_add_permission(self, request, obj=None):
        return False
