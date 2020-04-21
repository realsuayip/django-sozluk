from django.contrib import admin, messages as notifications

from ..models import GeneralReport


@admin.register(GeneralReport)
class GeneralReportAdmin(admin.ModelAdmin):
    search_fields = ("subject", "reporter_email")
    list_display = ("subject", "reporter_email", "category", "is_open")
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
        ("Rapor içeriği", {"fields": ("category", "subject", "content")}),
        ("Üstveri", {"fields": ("reporter_email", "date_created", "is_verified", "date_verified")}),
        ("Değerlendirme", {"fields": ("is_open",)}),
    )
    list_filter = ("category", "is_open")
    ordering = ("-is_verified", "-is_open")
    actions = ("close_report", "open_report")

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(is_verified=False)

    def close_report(self, request, queryset):
        queryset.update(is_open=False)
        notifications.success(request, "Seçilen raporların statüsü kapalı olarak işaretlendi")

    def open_report(self, request, queryset):
        queryset.update(is_open=True)
        notifications.success(request, "Seçilen raporların statüsü açık olarak işaretlendi")

    close_report.short_description = "Seçili raporlarının statüsünü kapalı olarak işaretle"
    open_report.short_description = "Seçili raporlarının statüsünü açık olarak işaretle"

    def has_add_permission(self, request, obj=None):
        return False
