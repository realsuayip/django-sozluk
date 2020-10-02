from django.contrib import admin
from django.contrib.admin import DateFieldListFilter, SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from django.urls import path
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _

from dictionary.admin.views.author import SuspendUser, UnsuspendUser
from dictionary.admin.views.novices import NoviceList, NoviceLookup
from dictionary.models import Author
from dictionary.utils.admin import intermediate


class SuspensionFilter(SimpleListFilter):
    title = _("Suspension status")
    parameter_name = "suspended"

    def lookups(self, request, model_admin):
        return [("yes", gettext("Suspended")), ("no", gettext("Not suspended"))]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(suspended_until__gt=timezone.now())
        if self.value() == "no":
            return queryset.filter(Q(suspended_until__lt=timezone.now()) | Q(suspended_until__isnull=True))

        return None


@admin.register(Author)
class AuthorAdmin(UserAdmin):
    search_fields = ("username",)
    autocomplete_fields = ("badges",)
    list_display = ("username", "email", "is_active", "is_novice", "karma", "date_joined")
    ordering = ("-date_joined",)

    list_filter = (
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
        SuspensionFilter,
        "is_frozen",
        "is_private",
        "gender",
        "badges",
        "is_novice",
        "application_status",
        ("date_joined", DateFieldListFilter),
    )

    fieldsets = (
        (None, {"fields": ("username", "karma", "badges")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "gender", "birth_date")},),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Accessibility details"), {"fields": ("is_frozen", "is_private", "suspended_until")}),
        (
            _("Novice status"),
            {"fields": ("is_novice", "application_status", "application_date", "last_activity", "queue_priority")},
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    readonly_fields = (
        "email",
        "gender",
        "birth_date",
        "application_date",
        "last_activity",
        "last_login",
        "date_joined",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        return self.readonly_fields

    add_fieldsets = ((None, {"fields": ("email",)}),) + UserAdmin.add_fieldsets
    actions = ("suspend_user", "unsuspend_user")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("novices/list/", self.admin_site.admin_view(NoviceList.as_view()), name="novice_list"),
            path(
                "novices/lookup/<str:username>/",
                self.admin_site.admin_view(NoviceLookup.as_view()),
                name="novice_lookup",
            ),
            path("actions/suspend/", self.admin_site.admin_view(SuspendUser.as_view()), name="suspend-user"),
            path("actions/unsuspend/", self.admin_site.admin_view(UnsuspendUser.as_view()), name="unsuspend-user"),
        ]

        return custom_urls + urls

    # Custom permissions for action | pylint: disable=R0201
    def has_suspension_permission(self, request):
        """Does the user have the user (un)suspension permission?"""
        return request.user.has_perm("dictionary.suspend_user")

    # Actions
    @intermediate
    def suspend_user(self, request, queryset):
        return "admin:suspend-user"

    @intermediate
    def unsuspend_user(self, request, queryset):
        return "admin:unsuspend-user"

    # Short descriptions
    suspend_user.short_description = _("Suspend selected authors")
    unsuspend_user.short_description = _("Unsuspend selected authors")

    # Permissions
    suspend_user.allowed_permissions = ["suspension"]
    unsuspend_user.allowed_permissions = ["suspension"]
