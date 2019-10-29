from django.urls import path
from .views import (index, Logout, Login, SignUp, topic, topic_list, user_profile, messages, conversation,
                    _autocomplete, _favorite, _category, _compose_message, _vote, _user_actions, people, _entry_actions,
                    _topic_actions)

# todo convert all of paths to views.<ViewName>
from . import views

urlpatterns_ajax = [path('entry/favorite/', _favorite, name="favorite"), path('entry/vote/', _vote, name="vote"),
                    path('category/<slug:slug>/', _category, name="cateogry"),
                    path('mesaj/gonder/', _compose_message, name="compose_message"),
                    path('user/action/', _user_actions, name="user_actions"),
                    path('entry/action/', _entry_actions, name="entry_actions"),
                    path('t/action/', _topic_actions, name="topic_actions")]

urlpatterns = urlpatterns_ajax + [path('', index, name="home"), path('login/', Login.as_view(), name="login"),
                                  path('register/', SignUp.as_view(), name="register"),
                                  path('logout/', Logout.as_view(next_page="/"), name="logout"),
                                  path('biri/<str:username>/', user_profile, name="user_profile"),
                                  path('topic/', topic, name="topic_search"),
                                  path('topic/<slug:slug>/', topic, name="topic"),
                                  path('topic/<str:unicode>/', topic, name="topic_unicode_url"),
                                  path('basliklar/<slug:slug>/', topic_list, name="topic_list"),
                                  path('entry/<int:entry_id>/', topic, name="entry_permalink"),
                                  path('entry/update/<int:pk>/', views.EntryUpdate.as_view(), name="entry_update"),
                                  path('autocomplete/general/', _autocomplete, name="autocomplete"),
                                  path('mesaj/', messages, name="messages"),
                                  path('mesaj/<str:username>/', conversation, name="conversation"),
                                  path('takip-engellenmis/', people, name="people"),
                                  path('olay/', views.ActivityList.as_view(), name="activity"),
                                  path("kanallar/", views.CategoryList.as_view(), name="category_list"),
                                  path("ayarlar/", views.UserPreferences.as_view(), name="user_preferences"),
                                  path("ayarlar/sifre/", views.ChangePassword.as_view(),
                                       name="user_preferences_password")]
