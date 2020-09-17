from django.urls import path

from dictionary.views.list import CategoryList, Index, TopicEntryList, TopicList

urlpatterns_list = [
    # Generic list
    path("", Index.as_view(), name="home"),
    path("threads/<slug:slug>/", TopicList.as_view(), name="topic_list"),
    path("channels/", CategoryList.as_view(), name="category_list"),
    # Topic entry list
    path("topic/", TopicEntryList.as_view(), name="topic-search"),
    path("topic/<slug:slug>/", TopicEntryList.as_view(), name="topic"),
    path("topic/<str:unicode_string>/", TopicEntryList.as_view(), name="topic-unicode-url"),
    path("entry/<int:entry_id>/", TopicEntryList.as_view(), name="entry-permalink"),
]
