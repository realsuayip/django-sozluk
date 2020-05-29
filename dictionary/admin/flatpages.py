from django.contrib.flatpages.admin import FlatPageAdmin as _FlatPageAdmin
from django.db import models
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _


class FlatPageAdmin(_FlatPageAdmin):
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 25, "style": "width: 100%; box-sizing: border-box;"})},
    }
    list_display = ("url", "title", "weight")
    fieldsets = (
        (None, {"fields": ("url", "title", "content", "html_only", "weight", "sites")}),
        (_("Advanced options"), {"classes": ("collapse",), "fields": ("registration_required", "template_name")}),
    )
