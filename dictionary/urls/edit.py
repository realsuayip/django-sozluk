from django.urls import path

from ..views.edit import EntryUpdate
from ..views.reporting import GeneralReportView


urlpatterns_edit = [
    path('entry/update/<int:pk>/', EntryUpdate.as_view(), name="entry_update"),
    path('iletisim/', GeneralReportView.as_view(), name="general-report"),
]
