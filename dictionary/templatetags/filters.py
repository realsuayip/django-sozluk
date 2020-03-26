import calendar
import re
from datetime import datetime

from django import template
from django.utils.html import escape, mark_safe

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
    """
    Formats custom entry tags (e.g. hede, spoiler. Tag explanations given in order with replacements tuple.
    1) Input: (bkz: #90), Output: unchanged, but #90 has link to entry with the id of 90. Allow only positive integers
    after '#', up to 10 digits.
    2) Input: (bkz: unicode topic title), Output: unchanged, but 'unicode topic title' has a link that points to the
    entry list view of that topic. No trailing whitespace allowed, only allow numbers and turkish alphabetical chars.
    3) Input: (bkz: @username), Output: unchanged, but '@username' has a link that points to the that users profile.
    Returns 404 if not exists. No trailing whitespace allowed. Only allow latin (lowercase) a-z and spaces between.
    4) Input: `:swh`, Output: * (an asterisks) -- This is a link that points to the topic 'swh', same rules of (2)
    5) Input: `#90`, Output: #90 -- This is a link that points to the entry with pk 90, same rules of (1)
    6) Input: `unicode topic title` Output: unicode topic title -- A link that points to the topic, same rules of (2)
    7) Input: (ara: beni yar) Output: unchanged, but 'beni yar' has a link that, when clicked searchs for that keyword
    in topics and appends to the left frame (redirects to the advanced search page on mobile). Same rules of (2)
    8) Input: [http://www.djangoproject.com django] Output: django -- A link that opens http://www.djangoproject.com in
    a new tab. Protocol name (http/https only) required. Rules for text is the same as (2)
    """
    entry = escape(raw_entry)  # Prevent XSS
    replacements = (
        (r"\(bkz: #([1-9]\d{0,10})\)", r'(bkz: <a href="/entry/\1">#\1</a>)'),
        (r"\(bkz: (?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)\)", r'(bkz: <a href="/topic/?q=\1">\1</a>)'),
        (r"\(bkz: @(?!\s)([a-z\ ]+)(?<!\s)\)", r'(bkz: <a href="/biri/\1/">@\1</a>)'),
        (
            r"`:(?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)`",
            r'<a data-sup="(bkz: \1)" href="/topic/?q=\1" title="(bkz: \1)">*</a>',
        ),
        (r"`#([1-9]\d{0,10})`", r'<a href="/entry/\1">#\1</a>'),
        (r"`(?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)`", r'<a href="/topic/?q=\1">\1</a>'),
        (
            r"\(ara: (?!\s)(@?[a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)\)",
            r'(ara: <a data-keywords="\1" class="quicksearch" role="button" tabindex="0">\1</a>)',
        ),
        (
            r"\[(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}"
            r"|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}) (?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)\]",
            r'<a rel="nofollow noopener" target="_blank" href="\1">\2</a>',
        ),
    )

    for tag in replacements:
        entry = re.sub(*tag, entry)

    return mark_safe(entry)


@register.filter
def timestamp(date):
    return int(calendar.timegm(date.timetuple()))


@register.filter
def entrydate(created, edited):
    append = ""
    if edited is not None:
        if created.date() == edited.date():
            append = datetime.strftime(edited, " ~ %H:%M")
        else:
            append = datetime.strftime(edited, " ~ %d.%m.%Y %H:%M")

    return datetime.strftime(created, "%d.%m.%Y %H:%M") + append
