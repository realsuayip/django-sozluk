import calendar
import re

from django import template
from django.core.validators import ValidationError
from django.utils.html import escape, mark_safe
from uuslug import slugify

from ..models import Topic


register = template.Library()

"""
Make sure you restart the Django development
server every time you modify template tags.
"""


@register.filter
def addstr(arg1, arg2):
    """concatenate arg1 & arg2"""
    return str(arg1) + str(arg2)


@register.filter
def formatted(raw_entry):
    # todo: @admin ve #1 için ayrı -> şöyle (@admin) (#1)
    entry = escape(raw_entry)
    entry_bkz = re.sub(r'\(bkz: ([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]*)\)', r'(bkz: <a href="/topic/?q=\1">\1</a>)', entry)
    entry_swh = re.sub(r'`:([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]*)`', r'<a href="/topic/?q=\1" title="(bkz: \1)">*</a>', entry_bkz)
    entry_hede = re.sub(r'`([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]*)`', r'<a href="/topic/?q=\1">\1</a>', entry_swh)
    entry_link = re.sub(
        r'\[(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+'
        r'[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,}) '
        r'([a-zA-Z0-9 ğüşöçİĞÜŞÖÇ]*)\]', r'<a target="_blank" href="\1">\2</a>', entry_hede)

    return mark_safe(entry_link)


@register.filter
def is_valid_topic_title(topic_title):
    # If it is already created, it is most likely valid, huh?
    if Topic.objects.filter(title=topic_title).exists():
        return True

    if not slugify(topic_title):
        return False

    try:
        Topic(title=topic_title).full_clean()
    except ValidationError:
        return False

    return True


@register.filter
def timestamp(date):
    return int(calendar.timegm(date.timetuple()))
