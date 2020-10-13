from django.db.models import F
from django.utils import timezone

from dictionary.models import Author
from dictionary.utils import time_threshold


class NoviceActivityMiddleware:
    """
    Novice users who visits the website daily should have advantage on novice
    list, so we need to track last active date of novice users.
    """

    def __init__(self, get_response):
        self.get_response = get_response  # One-time configuration and initialization.

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and request.user.is_novice
            and request.user.application_status == "PN"
            and request.user.is_accessible
        ):
            last_activity = request.user.last_activity
            if last_activity is None or last_activity < time_threshold(hours=24):
                Author.objects.filter(id=request.user.id).update(
                    last_activity=timezone.now(), queue_priority=F("queue_priority") + 1
                )
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        return response
