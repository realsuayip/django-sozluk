from django.contrib import admin
from django.contrib.admin import DateFieldListFilter, SimpleListFilter
from django.db import models
from django.forms import Textarea
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from dictionary.models.announcements import Announcement


class PublishFilter(SimpleListFilter):
    title = _("Publish status")
    parameter_name = "published"

    def lookups(self, request, model_admin):
        return [("yes", gettext("Published")), ("no", gettext("Waiting for publication date"))]

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
    list_filter = (PublishFilter, ("date_created", DateFieldListFilter), "html_only", "notify")
    list_display = ("title", "discussion", "date_created")
    ordering = ("-date_created",)
