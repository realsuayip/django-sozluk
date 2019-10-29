from django import template
from ..util import banned_topics
import re
from django.utils.html import escape, mark_safe
import time
import calendar

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
        r'\[(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,}) ([a-zA-Z0-9 ğüşöçİĞÜŞÖÇ]*)\]',
        r'<a target="_blank" href="\1">\2</a>', entry_hede)

    return mark_safe(entry_link)


@register.filter
def classified(author_list):
    authors = []
    novices = []
    for person in author_list:
        if person.is_novice:
            novices.append(person)
        else:
            authors.append(person)
    return [authors, novices]


@register.filter
def banned_topic(topic_title):
    if topic_title in banned_topics:
        return True
    else:
        return False


@register.filter
def timestamp(date):
    # does not work at all todo
    return int(calendar.timegm(date.timetuple()))
