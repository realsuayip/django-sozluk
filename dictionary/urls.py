from django.urls import path
from .views import (index, Logout, Login, SignUp, topic, user_profile, messages, conversation, people)

# todo convert all of paths to views.<ViewName>
from . import views

from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetCompleteView, \
    PasswordResetConfirmView

urlpatterns_ajax = [
    path('entry/vote/', views.Vote.as_view(), name="vote"),
    path('category/<slug:slug>/', views.AsyncTopicList.as_view(), name="cateogry"),
    path('mesaj/action/gonder/', views.ComposeMessage.as_view(), name="compose_message"),
    path('user/action/', views.UserAction.as_view(), name="user_actions"),
    path('entry/action/', views.EntryAction.as_view(), name="entry_actions"),
    path('t/action/', views.TopicAction.as_view(), name="topic_actions"),
    path('autocomplete/general/', views.AutoComplete.as_view(), name="autocomplete"),
]

urlpatterns_password_reset = [
    path("parola/", PasswordResetView.as_view(
        template_name="registration/password_reset/form.html",
        html_email_template_name="registration/password_reset/email_template.html"),
        name="password_reset"),

    path("parola/oldu/", PasswordResetDoneView.as_view(
        template_name="registration/password_reset/done.html"),
        name="password_reset_done"),

    path("parola/onay/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name="registration/password_reset/confirm.html"),
        name="password_reset_confirm"),

    path("parola/tamam/", PasswordResetCompleteView.as_view(
        template_name="registration/password_reset/complete.html"),
         name="password_reset_complete"),
]

urlpatterns_regular = [path('', index, name="home"),
                       path('login/', Login.as_view(), name="login"),
                       path('register/', SignUp.as_view(), name="register"),
                       path('logout/', Logout.as_view(next_page="/"), name="logout"),
                       path('biri/<str:username>/', user_profile, name="user_profile"),
                       path('topic/', topic, name="topic_search"),
                       path('topic/<slug:slug>/', topic, name="topic"),
                       path('topic/<str:unicode>/', topic, name="topic_unicode_url"),
                       path('basliklar/<slug:slug>/', views.TopicList.as_view(), name="topic_list"),
                       path('entry/<int:entry_id>/', topic, name="entry_permalink"),
                       path('entry/update/<int:pk>/', views.EntryUpdate.as_view(), name="entry_update"),
                       path('mesaj/', messages, name="messages"),
                       path('mesaj/<str:username>/', conversation, name="conversation"),
                       path('takip-engellenmis/', people, name="people"),
                       path('olay/', views.ActivityList.as_view(), name="activity"),
                       path("kanallar/", views.CategoryList.as_view(), name="category_list"),
                       path("ayarlar/", views.UserPreferences.as_view(), name="user_preferences"),
                       path("ayarlar/sifre/", views.ChangePassword.as_view(), name="user_preferences_password"),
                       path("ayarlar/email/", views.ChangeEmail.as_view(), name="user_preferences_email"),
                       path("email/onayla/<uidb64>/<token>/", views.ConfirmEmail.as_view(), name="confirm_email"),
                       path("email/tekrar/", views.ResendEmailConfirmation.as_view(), name="resend_email")
                       ]

urlpatterns = urlpatterns_regular + urlpatterns_ajax + urlpatterns_password_reset
