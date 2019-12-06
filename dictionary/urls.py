from django.urls import path
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetCompleteView, \
    PasswordResetConfirmView

from .views.auth import Login, Logout, SignUp, ConfirmEmail, ResendEmailConfirmation, ChangePassword, ChangeEmail
from .views.detail import Chat, UserProfile
from .views.edit import UserPreferences, EntryUpdate
from .views.json import AsyncTopicList, AutoComplete, UserAction, EntryAction, TopicAction, ComposeMessage, Vote
from .views.list import PeopleList, ConversationList, ActivityList, CategoryList, TopicList, TopicEntryList, index
from .views.reporting import GeneralReportView

urlpatterns_json = [
    path('entry/vote/', Vote.as_view(), name="vote"),
    path('category/<slug:slug>/', AsyncTopicList.as_view(), name="cateogry"),
    path('mesaj/action/gonder/', ComposeMessage.as_view(), name="compose_message"),
    path('user/action/', UserAction.as_view(), name="user_actions"),
    path('entry/action/', EntryAction.as_view(), name="entry_actions"),
    path('t/action/', TopicAction.as_view(), name="topic_actions"),
    path('autocomplete/general/', AutoComplete.as_view(), name="autocomplete"),
]

urlpatterns_password_reset = [
    path("parola/", PasswordResetView.as_view(
        template_name="dictionary/registration/password_reset/form.html",
        html_email_template_name="registration/password_reset/email_template.html"),
        name="password_reset"),

    path("parola/oldu/", PasswordResetDoneView.as_view(
        template_name="dictionary/registration/password_reset/done.html"),
        name="password_reset_done"),

    path("parola/onay/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name="dictionary/registration/password_reset/confirm.html"),
        name="password_reset_confirm"),

    path("parola/tamam/", PasswordResetCompleteView.as_view(
        template_name="dictionary/registration/password_reset/complete.html"),
         name="password_reset_complete"),
]


urlpatterns_regular = [
    # General views
    path('', index, name="home"),
    path('basliklar/<slug:slug>/', TopicList.as_view(), name="topic_list"),
    path("kanallar/", CategoryList.as_view(), name="category_list"),
    path('biri/<str:username>/', UserProfile.as_view(), name="user-profile"),

    # Topic entry list
    path("topic/", TopicEntryList.as_view(), name="topic-search"),
    path("topic/<slug:slug>/", TopicEntryList.as_view(), name="topic"),
    path("topic/<str:unicode_string>/", TopicEntryList.as_view(), name="topic-unicode-url"),
    path('entry/<int:entry_id>/', TopicEntryList.as_view(), name="entry-permalink"),

    # User authentication
    path('login/', Login.as_view(), name="login"),
    path('register/', SignUp.as_view(), name="register"),
    path('logout/', Logout.as_view(next_page="/"), name="logout"),
    path("email/onayla/<uidb64>/<token>/", ConfirmEmail.as_view(), name="confirm_email"),
    path("email/tekrar/", ResendEmailConfirmation.as_view(), name="resend_email"),

    # User specific settings and views
    path("ayarlar/", UserPreferences.as_view(), name="user_preferences"),
    path("ayarlar/sifre/", ChangePassword.as_view(), name="user_preferences_password"),
    path("ayarlar/email/", ChangeEmail.as_view(), name="user_preferences_email"),
    path('takip-engellenmis/', PeopleList.as_view(), name="people"),
    path('olay/', ActivityList.as_view(), name="activity"),
    path('mesaj/', ConversationList.as_view(), name="messages"),
    path('mesaj/<str:username>/', Chat.as_view(), name="conversation"),

    # Other views
    path('entry/update/<int:pk>/', EntryUpdate.as_view(), name="entry_update"),
    path('iletisim/', GeneralReportView.as_view(), name="general-report")
]

urlpatterns = urlpatterns_regular + urlpatterns_json + urlpatterns_password_reset
