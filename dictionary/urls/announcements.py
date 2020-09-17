from django.urls import path

from dictionary.views.announcements import AnnouncementDetail, AnnouncementIndex, AnnouncementMonth


urlpatterns_announcements = [
    path("announcements/", AnnouncementIndex.as_view(), name="announcements-index"),
    path(
        "announcements/<int:year>/<int:month>/",
        AnnouncementMonth.as_view(month_format="%m"),
        name="announcements-month",
    ),
    path(
        "announcements/<int:year>/<int:month>/<int:day>/<slug:slug>/",
        AnnouncementDetail.as_view(month_format="%m"),
        name="announcements-detail",
    ),
]
