from .models import Entry, Category, Topic, Author, TopicFollowing, UserVerification
import datetime
from django.shortcuts import get_object_or_404
from functools import wraps
from django.http import HttpResponseBadRequest, Http404
from django.utils import timezone
from decimal import Decimal
from dateutil.parser import parse
from django.urls import reverse_lazy
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.hashers import make_password
from django.core.cache import cache

"""
Custom settings
"""

DOMAIN = "127.0.0.1:8000"
PROTOCOL = "http"
FROM_EMAIL = "test@django.org"

# time difference of 1 day. if you are going to refactor this,
# please look for usages beforehand [there are a lot of usages].
time_threshold_24h = timezone.now() - datetime.timedelta(hours=24)
YEAR_RANGE = list(reversed(range(2017, 2020)))  # also set in djdict.js, reversed so as the latest year is on
ENTRIES_PER_PAGE = 10
TOPICS_PER_PAGE = 2  # experimental
ENTRIES_PER_PAGE_PROFILE = 15
nondb_categories = ["bugun", "gundem", "basiboslar", "tarihte-bugun", "kenar", "caylaklar", "takip", "debe"]
exclusively_cache = ["bugun", "debe", "kenar", "takip", "tarihte-bugun"]
banned_topics = [  # include banned topics here
    " ", "@", " % ", "seks"]
cache_timeout = 60  # 1 minutes, for non-exclusive slugs
vote_rates = {"favorite": Decimal(".2"), "increase": Decimal(".2"), "reduce": Decimal("-.2"),
              "anonymous_multiplier": Decimal(".5"), "authenticated_multiplier": Decimal("1")}


def categories():
    """
    Provides category list for header.
    """
    return Category.objects.all()


def require_ajax(view):
    @wraps(view)
    def _wrapped_view(request, *args, **kwargs):
        if request.is_ajax():
            return view(request, *args, **kwargs)
        else:
            return HttpResponseBadRequest()

    return _wrapped_view


def get_current_path(request):
    return {'current_path': request.get_full_path()}


def find_after_page(pages_before):
    is_on = pages_before + 1
    page_count = 0
    while is_on > 0:
        page_count += 1
        is_on -= ENTRIES_PER_PAGE
    if is_on == 0:
        page_count += 1
    return page_count


def mark_read(topic, user):
    """
    Marks the topic read, if user is following it.
    """
    try:
        obj = TopicFollowing.objects.get(topic=topic, author=user)
    except TopicFollowing.DoesNotExist:
        return False
    obj.read_at = timezone.now()
    obj.save()
    return True


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return str(user.pk) + str(timestamp) + str(user.is_active)


def send_email_confirmation(user, to_email):
    token_generator = EmailVerificationTokenGenerator()
    verification_token_raw = token_generator.make_token(user)
    verification_token_hashed = make_password(verification_token_raw)
    expiration_date = timezone.now() + datetime.timedelta(days=1)
    UserVerification.objects.create(author=user, verification_token=verification_token_hashed,
                                    expiration_date=expiration_date, new_email=to_email)

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    params = {"domain": DOMAIN, "protocol": PROTOCOL, "user": user, "uidb64": uidb64, "token": verification_token_raw}
    msg = render_to_string("registration/email_confirmation.html", params)
    return send_mail("email onayı", "email onayı", from_email=FROM_EMAIL, recipient_list=[to_email], html_message=msg,
                     fail_silently=True)


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
            if not last_activity or parse(last_activity) < time_threshold_24h:
                Author.objects.filter(id=request.user.id).update(last_activity=timezone.now())
                request.session[self.KEY] = timezone.now().isoformat()
                # Determines the novice queue number on profile page
                # it finds ALL the novices on the list whose queue number is before the user, having the equals to adds
                # +1 to the number, giving the current users queue number
                queue = Author.objects.filter(is_novice=True, application_status="PN",
                                              last_activity__gte=time_threshold_24h,
                                              application_date__lte=request.user.application_date).count()
                request.session['novice_queue'] = queue
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        response = self.get_response(request)
        # Code to be executed for each request/response after
        # the view is called.
        return response
