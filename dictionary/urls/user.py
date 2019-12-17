from django.urls import path

from ..views.detail import Chat, UserProfile
from ..views.edit import UserPreferences
from ..views.list import PeopleList, ConversationList, ActivityList

urlpatterns_user = [
    # user related urls
    path("ayarlar/", UserPreferences.as_view(), name="user_preferences"),
    path('takip-engellenmis/', PeopleList.as_view(), name="people"),
    path('olay/', ActivityList.as_view(), name="activity"),
    path('mesaj/', ConversationList.as_view(), name="messages"),
    path('mesaj/<str:username>/', Chat.as_view(), name="conversation"),
    path('biri/<str:username>/', UserProfile.as_view(), name="user-profile"),
]
