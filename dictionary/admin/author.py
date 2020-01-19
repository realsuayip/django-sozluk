from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path

from ..models import Author
from ..utils.admin import IntermediateActionHandler
from .views.author import SuspendUser, UnsuspendUser
from .views.novices import NoviceList, NoviceLookup


@admin.register(Author)
class AuthorAdmin(UserAdmin):
    model = Author
    raw_id_fields = ['upvoted_entries', 'downvoted_entries', 'following', 'blocked', 'pinned_entry']
    search_fields = ["username"]
    list_display = ("username", "email", "is_active", "is_novice", "date_joined")

    fieldsets = UserAdmin.fieldsets + ((None, {'fields': (
        'is_novice', 'application_status', 'application_date', 'last_activity', 'suspended_until', 'birth_date',
        'gender', 'following', "blocked", 'upvoted_entries', 'downvoted_entries', 'pinned_entry',
        "following_categories")}),)

    add_fieldsets = ((None, {'fields': ('email',)}),) + UserAdmin.add_fieldsets
    actions = ("suspend_user", "unsuspend_user")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [path('novices/list/', self.admin_site.admin_view(NoviceList.as_view()), name="novice_list"),
                       path('novices/lookup/<str:username>/', self.admin_site.admin_view(NoviceLookup.as_view()),
                            name="novice_lookup"),
                       path('actions/suspend/', self.admin_site.admin_view(SuspendUser.as_view()), name="suspend-user"),
                       path('actions/unsuspend/', self.admin_site.admin_view(UnsuspendUser.as_view()),
                            name="unsuspend-user"), ]

        return custom_urls + urls

    # Custom permissions for action
    def has_suspension_permission(self, request):
        """Does the user have the user (un)suspension permission?"""
        return request.user.has_perm("dictionary.suspend_user")

    # Actions
    def suspend_user(self, request, queryset):
        action = IntermediateActionHandler(queryset, "admin:suspend-user")
        return action.redirect_url

    def unsuspend_user(self, request, queryset):
        action = IntermediateActionHandler(queryset, "admin:unsuspend-user")
        return action.redirect_url

    # Short descriptions
    suspend_user.short_description = f"Seçili {model._meta.verbose_name_plural} nesnelerini askıya al"
    unsuspend_user.short_description = f"Seçili {model._meta.verbose_name_plural} nesnelerini askıdan kaldır"

    # Permissions
    suspend_user.allowed_permissions = ["suspension"]
    unsuspend_user.allowed_permissions = ["suspension"]
