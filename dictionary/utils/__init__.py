import datetime
from contextlib import suppress

from django.contrib.auth import get_user_model
from django.http import Http404
from django.utils import timezone

from dateutil.parser import parse

from .settings import GENERIC_SUPERUSER_ID


# General utilities module. DO NOT IMPORT FROM models. Use: apps.get_model("app_name", "model_name")


class proceed_or_404(suppress):
    """If the supplied exceptions occur in a block of code, raise Http404"""

    def __exit__(self, exctype, excinst, exctb):
        failed = super().__exit__(exctype, excinst, exctb)

        if failed:
            raise Http404


def turkish_lower(turkish_string):
    lower_map = {ord("I"): "ı", ord("İ"): "i"}
    return turkish_string.translate(lower_map).lower()


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


def get_generic_superuser():
    return get_user_model().objects.get(pk=GENERIC_SUPERUSER_ID)


def get_category_parameters(slug, year):
    pairs = {
        **dict.fromkeys(("bugun", "gundem", "basiboslar", "generic"), "?a=today"),
        "tarihte-bugun": f"?a=history&year={year}",
        "caylaklar": "?a=novices",
        "son": "?a=recent",
    }

    return pairs.get(slug)


class InputNotInDesiredRangeError(Exception):
    pass
