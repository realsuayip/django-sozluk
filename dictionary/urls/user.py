from django.urls import path

from ..views.detail import Chat, UserProfile
from ..views.edit import UserPreferences
from ..views.list import ActivityList, ConversationList, PeopleList


urlpatterns_user = [
    # user related urls
    path("settings/", UserPreferences.as_view(), name="user_preferences"),
    path("people/", PeopleList.as_view(), name="people"),
    path("activity/", ActivityList.as_view(), name="activity"),
    path("messages/", ConversationList.as_view(), name="messages"),
    path("messages/<slug:slug>/", Chat.as_view(), name="conversation"),
    path("author/<slug:slug>/", UserProfile.as_view(), name="user-profile"),
]
