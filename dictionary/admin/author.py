from django.contrib.auth.admin import UserAdmin
from django.urls import path

from . import Author
from ..views.admin.novices import NoviceList, NoviceLookup


class AuthorAdmin(UserAdmin):
    model = Author
    raw_id_fields = ['favorite_entries', 'upvoted_entries', 'downvoted_entries', 'following', 'blocked', 'pinned_entry']

    fieldsets = UserAdmin.fieldsets + ((None, {'fields': (
        'is_novice', 'application_status', 'application_date', 'last_activity', 'banned_until', 'birth_date', 'gender',
        'following', "blocked", 'favorite_entries', 'upvoted_entries', 'downvoted_entries', 'pinned_entry')}),)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('novices/list/', self.admin_site.admin_view(NoviceList.as_view()), name="novice_list"),
                   path('novices/lookup/<str:username>/', self.admin_site.admin_view(NoviceLookup.as_view()),
                        name="novice_lookup"), ]
        return my_urls + urls
