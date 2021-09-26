import datetime
import re

from contextlib import suppress

from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone
from django.utils.translation import get_language

from dateutil.parser import parse

from dictionary.conf import settings
from dictionary.utils.decorators import cached_context

# General utilities module. DO NOT IMPORT FROM models. Use: apps.get_model("app_name", "model_name")

RE_WEBURL = (
    r"((?:(?:(?:https?):)\/\/)(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1[6-"
    r"9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?:["
    r"1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z0-9][a-z0-9_-]{0,62})?[a-z0-9]\.)+(?:[a-z]{2,}\.?))(?::\d{2,5})?)((?:["
    r"/?#](?:(?![\s\"<>{}|\\^~\[\]`])(?!&lt;|&gt;|&quot;|&#x27;).)*))?"
)
"""This is a modified version of Diego Perini's weburl regex. (https://gist.github.com/dperini/729294)"""

RE_WEBURL_NC = (
    r"(?:(?:(?:(?:https?):)\/\/)(?:(?!(?:10|127)(?:\.\d{1,3}){3})(?!(?:169\.254|192\.168)(?:\.\d{1,3}){2})(?!172\.(?:1["
    r"6-9]|2\d|3[0-1])(?:\.\d{1,3}){2})(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5])){2}(?:\.(?"
    r":[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))|(?:(?:[a-z0-9][a-z0-9_-]{0,62})?[a-z0-9]\.)+(?:[a-z]{2,}\.?))(?::\d{2,5})?)(?:"
    r"(?:[/?#](?:(?![\s\"<>{}|\\^~\[\]`])(?!&lt;|&gt;|&quot;|&#x27;).)*))?"
)
"""RE_WEBURL but with no capturing groups."""


class proceed_or_404(suppress):
    """If the supplied exceptions occur in a block of code, raise Http404"""

    def __exit__(self, exctype, excinst, exctb):
        failed = super().__exit__(exctype, excinst, exctb)

        if failed:
            raise Http404


def i18n_lower(value):
    # Currently we only support English and Turkish, this rule
    # (İ -> i) can be applied to the both of the languages.
    lower_map = {ord("İ"): "i"}

    if get_language() == "tr":
        lower_map.update({ord("I"): "ı"})

    return value.translate(lower_map).lower()

def smart_lower(value):
    url_nc = re.compile(f"({RE_WEBURL_NC})")

    # Links should not be lowered
    if url_nc.search(value):
        substrings = url_nc.split(value)
        for idx, substr in enumerate(substrings):
            if not url_nc.match(substr):
                substrings[idx] = i18n_lower(substr)
        return "".join(substrings)

    return i18n_lower(value)


def parse_date_or_none(date_string, delta=None, dayfirst=True, **timedelta_kwargs):
    """
    Return a django timezone aware date object if string is parsable else None.
    :param date_string: A string containing a date
    :param delta: 'negative' or 'positive'. A date string such as '01.02.2010' is parsed into a datetime string whose
    time is on midnight. So if you want that time to be included in range you should deduct 1 day so that you can get a
    range starting from night of (00:00) that particular day. You can also include time directly in date_string such as
    '12.02.2010 06:00' etc.
    :param dayfirst: set false if date_string doesn't start with day
    :param timedelta_kwargs: kwargs for datetime.timedelta
    """

    if not isinstance(date_string, str) or not date_string:
        return None

    if delta and delta not in ("positive", "negative"):
        raise ValueError("Invalid delta option. Options are 'positive' or 'negative'")

    try:
        # Check if date is parsable (raises ValueError if not)
        parsed_date = parse(date_string, dayfirst=dayfirst)
    except (ValueError, OverflowError):
        return None

    # Calculate timedalte if delta & kargsa are specified
    if delta == "negative":
        parsed_date = parsed_date - datetime.timedelta(**timedelta_kwargs)
    elif delta == "positive":
        parsed_date = parsed_date + datetime.timedelta(**timedelta_kwargs)

    # Convert it to timezone aware date object
    return timezone.make_aware(parsed_date)


def time_threshold(**timedelta_kwargs):
    """Return (timedelta **kwargs, e.g. days=1) ago, from now."""
    return timezone.now() - datetime.timedelta(**timedelta_kwargs)


@cached_context
def get_generic_superuser():
    return get_user_model().objects.get(username=settings.GENERIC_SUPERUSER_USERNAME)


def get_generic_privateuser():
    return get_user_model().objects.get(username=settings.GENERIC_PRIVATEUSER_USERNAME)


def get_theme_from_cookie(request):
    themes = ("dark", "light")

    if (theme := request.COOKIES.get("theme", "light")) in themes:
        return theme

    return "light"


class InputNotInDesiredRangeError(Exception):
    pass
