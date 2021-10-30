from django.contrib import messages as notifications
from django.urls import reverse_lazy
from django.utils.translation import gettext
from django.views.generic import RedirectView


class OAuthFailRedirectView(RedirectView):
    url = reverse_lazy("login")

    def get(self, request, *args, **kwargs):
        notifications.error(
            request,
            gettext(
                "Authentication via social account could not be completed."
                " Make sure the associated email is not already in use."
            ),
            extra_tags="persistent",
        )
        return super().get(request, *args, **kwargs)
