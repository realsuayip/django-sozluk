from django.urls import path

from dictionary.views.edit import CommentCreate, CommentUpdate, EntryCreate, EntryUpdate
from dictionary.views.reporting import GeneralReportView

urlpatterns_edit = [
    path("entry/update/<int:pk>/", EntryUpdate.as_view(), name="entry_update"),
    path("entry/create/", EntryCreate.as_view(), name="entry_create"),
    path("entry/<int:pk>/comment/", CommentCreate.as_view(), name="comment_create"),
    path("entry/comment/edit/<int:pk>/", CommentUpdate.as_view(), name="comment_update"),
    path("contact/", GeneralReportView.as_view(), name="general-report"),
]
