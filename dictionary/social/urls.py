from django.urls import include, path

from dictionary.social.views import OAuthFailRedirectView

urlpatterns = [
    path(
        "fail/",
        OAuthFailRedirectView.as_view(),
        name="socialaccount_signup",
    ),
    path("", include("allauth.socialaccount.providers.google.urls")),
]
