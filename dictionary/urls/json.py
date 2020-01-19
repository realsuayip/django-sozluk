from django.urls import path

from ..views.json import (AsyncTopicList, AutoComplete, CategoryAction, ComposeMessage, EntryAction, TopicAction,
                          UserAction, Vote)


urlpatterns_json = [
    path('entry/vote/', Vote.as_view(), name="vote"),
    path('category/<slug:slug>/', AsyncTopicList.as_view(), name="cateogry"),
    path('mesaj/action/gonder/', ComposeMessage.as_view(), name="compose_message"),
    path('user/action/', UserAction.as_view(), name="user_actions"),
    path('entry/action/', EntryAction.as_view(), name="entry_actions"),
    path('t/action/', TopicAction.as_view(), name="topic_actions"),
    path("c/action/", CategoryAction.as_view(), name="category_actions"),
    path('autocomplete/general/', AutoComplete.as_view(), name="autocomplete"),
]
