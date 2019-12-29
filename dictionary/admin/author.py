from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import path

from ..models import Author
from ..admin.views.novices import NoviceList, NoviceLookup


@admin.register(Author)
class AuthorAdmin(UserAdmin):
    model = Author
    raw_id_fields = ['upvoted_entries', 'downvoted_entries', 'following', 'blocked', 'pinned_entry']
    search_fields = ["username"]
    list_display = ("username", "email", "is_active", "is_novice", "date_joined")

    fieldsets = UserAdmin.fieldsets + ((None, {'fields': (
        'is_novice', 'application_status', 'application_date', 'last_activity', 'banned_until', 'birth_date', 'gender',
        'following', "blocked", 'upvoted_entries', 'downvoted_entries', 'pinned_entry',
        "following_categories")}),)

    add_fieldsets = ((None, {'fields': ('email',)}),) + UserAdmin.add_fieldsets

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('novices/list/', self.admin_site.admin_view(NoviceList.as_view()), name="novice_list"),
                   path('novices/lookup/<str:username>/', self.admin_site.admin_view(NoviceLookup.as_view()),
                        name="novice_lookup"), ]
        return my_urls + urls
