from django.urls import path

from ..views.json import Vote


urlpatterns_json = [
    path('entry/vote/', Vote.as_view(), name="vote"),
]
