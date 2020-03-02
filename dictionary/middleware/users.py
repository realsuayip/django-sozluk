from django.utils import timezone

from dateutil.parser import parse

from ..models import Author
from ..utils import time_threshold


class NoviceActivityMiddleware:
    """
    https://stackoverflow.com/questions/18434364/django-get-last-user-visit-date/39064596#39064596
    Novice users who visits the website daily should have advantage on novice list, so we need to track last active date
    of novice users, which is what this middleware does. (And also determines novice queue number)
    """
    KEY = "last_activity"

    def __init__(self, get_response):
        self.get_response = get_response  # One-time configuration and initialization.

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_novice and request.user.application_status == "PN":
            last_activity = request.session.get(self.KEY)
            if not last_activity or parse(last_activity) < time_threshold(hours=24):
                Author.objects.filter(id=request.user.id).update(last_activity=timezone.now())
                request.session[self.KEY] = timezone.now().isoformat()
                # Determines the novice queue number on profile page
                # it finds ALL the novices on the list whose queue number is before the user, having the equals to adds
                # +1 to the number, giving the current users queue number
                queue = Author.objects.filter(is_novice=True, application_status="PN",
                                              last_activity__gte=time_threshold(hours=24),
                                              application_date__lte=request.user.application_date).count()
                request.session['novice_queue'] = queue
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        return response
