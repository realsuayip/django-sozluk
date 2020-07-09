from django.contrib import admin
from django.contrib.admin import DateFieldListFilter, SimpleListFilter
from django.db import models
from django.forms import Textarea
from django.utils import timezone

from ..models.announcements import Announcement


class PublishFilter(SimpleListFilter):
    title = "Yayınlanma durumu"
    parameter_name = "published"

    def lookups(self, request, model_admin):
        return [("yes", "Yayınlandı"), ("no", "Yayınlanma tarihini bekliyor")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(date_created__lte=timezone.now())
        if self.value() == "no":
            return queryset.filter(date_created__gte=timezone.now())

        return None


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 20, "style": "width: 50%; box-sizing: border-box;"})},
    }

    autocomplete_fields = ("discussion",)
    search_fields = ("title",)
    list_filter = (
        PublishFilter,
        ("date_created", DateFieldListFilter),
    )
    list_display = ("title", "date_created")
