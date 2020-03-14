import base64
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone

from dateutil.parser import parse

from .settings import GENERIC_SUPERUSER_ID


# General utilities module. DO NOT IMPORT FROM models. Use: apps.get_model("app_name", "model_name")

def turkish_lower(turkish_string):
    lower_map = {ord(u'I'): u'ı', ord(u'İ'): u'i'}
    return turkish_string.translate(lower_map).lower()


def parse_date_or_none(date_string, delta=None, dayfirst=True, **timedelta_kwargs):
    """
    Return a django timezone aware date object if string is parsable else None or False.
    :param date_string: A string containing a date
    :param delta: 'negative' or 'positive'. A date string such as '01.02.2010' is parsed into a datetime string whose
    time is on midnight. So if you want that time to be included in range you should deduct 1 day so that you can get a
    range starting from night of (00:00) that particular day. You can also include time directly in date_string such as
    '12.02.2010 06:00' etc.
    :param dayfirst: set false if date_string doesn't start with day
    :param timedelta_kwargs: kwargs for datetime.timedelta
    """

    if not isinstance(date_string, str) or not date_string:
        return False

    if delta and delta not in ('positive', 'negative'):
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


def get_generic_superuser():
    return get_user_model().objects.get(pk=GENERIC_SUPERUSER_ID)


def b64decode_utf8_or_none(b64_str):
    """Return decoded b64 string (utf-8), if the b64 cannot be decoded, return None"""
    if not b64_str:
        return None

    try:
        return base64.b64decode(b64_str).decode("utf-8")
    except (base64.binascii.Error, AttributeError, UnicodeDecodeError):
        return None


def get_category_parameters(slug, year):
    pairs = {  # @formatter:off
        "bugun": "?day=today",
        "gundem": "?day=today",
        "tarihte-bugun": f"?year={year}",
        "caylaklar": "?a=caylaklar",
        "generic": "?day=today",
        "basiboslar": "?day=today"
    }  # @formatter:on

    return pairs.get(slug)


class InputNotInDesiredRangeError(Exception):
    pass
