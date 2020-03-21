from django.urls import path

from ..views.json import EntryAction, Vote


urlpatterns_json = [
    path('entry/vote/', Vote.as_view(), name="vote"),
    path('entry/action/', EntryAction.as_view(), name="entry_actions"),
]
