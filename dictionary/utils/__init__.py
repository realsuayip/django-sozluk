import datetime

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import make_aware

from dateutil.parser import parse


# General utilities

def turkish_lower(turkish_string):
    lower_map = {ord(u'I'): u'ı', ord(u'İ'): u'i', }
    return turkish_string.translate(lower_map).lower()


def log_admin(msg, authorizer, model_type, model_object, flag=CHANGE):
    LogEntry.objects.log_action(user_id=authorizer.id, content_type_id=ContentType.objects.get_for_model(model_type).pk,
                                object_id=model_object.id, object_repr=f"{msg}", change_message=msg, action_flag=flag)


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
        return make_aware(parsed_date)
    except (ValueError, OverflowError):
        return None
