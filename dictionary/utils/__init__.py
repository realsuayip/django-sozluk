import datetime

from dateutil.parser import parse
from django.contrib.auth import get_user_model
from django.utils import timezone

from .settings import GENERIC_SUPERUSER_ID


# General utilities

def turkish_lower(turkish_string):
    lower_map = {ord(u'I'): u'ı', ord(u'İ'): u'i', }
    return turkish_string.translate(lower_map).lower()


def parse_date_or_none(date_string, delta=None, dayfirst=True, **kwargs):
    """
    Return a django timezone aware date object if string is parsable else None or False.
    :param date_string: A string containing a date
    :param delta: 'add' or 'sub'. A date string such as '01.02.2010' is parsed into a datetime string whose time is
    on midnight. So if you want that time to be included in range you should deduct 1 day so that you can get a range
    starting from night of (00:00) that particular day. You can also include time directly in date_string such as
    '12.02.2010 06:00' etc.
    :param dayfirst: set false if date_string doesn't start with day
    :param kwargs: kwargs for datetime.timedelta
    """

    if not isinstance(date_string, str) or not date_string:
        return False

    if delta and delta not in ('positive', 'negative'):
        raise ValueError("Invalid delta option. Options are 'positive' or 'negative'")

    try:
        # Check if date is parsable (raises ValueError if not)
        parsed_date = parse(date_string, dayfirst=dayfirst)

        # Calculate timedalte if delta & kargsa are specified
        if delta == "negative":
            parsed_date = parsed_date - datetime.timedelta(**kwargs)
        elif delta == "positive":
            parsed_date = parsed_date + datetime.timedelta(**kwargs)

        # Convert it to timezone aware date object
        return timezone.make_aware(parsed_date)
    except (ValueError, OverflowError):
        return None


def time_threshold(**kwargs):
    # Return (timedelta **kwargs, e.g. days=1) ago, from now.
    return timezone.now() - datetime.timedelta(**kwargs)


def get_generic_superuser():
    return get_user_model().objects.get(pk=GENERIC_SUPERUSER_ID)


class InputNotInDesiredRangeError(Exception):
    pass
