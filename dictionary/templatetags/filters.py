import re

from html import unescape
from urllib.parse import quote_plus

from django import template
from django.template import defaultfilters
from django.utils import timezone
from django.utils.html import escape, mark_safe
from django.utils.translation import gettext as _, gettext_lazy, pgettext_lazy

from dateutil.parser import parse

from dictionary.conf import settings
from dictionary.utils import RE_WEBURL, RE_WEBURL_NC


register = template.Library()

"""
Make sure you restart the Django development
server every time you modify template tags.
"""


@register.filter
def startswith(arg1, arg2):
    return arg1.startswith(arg2)


@register.filter
def addstr(arg1, arg2):
    """concatenate arg1 & arg2"""
    return str(arg1) + str(arg2)


RE_ENTRY_CHARSET = r"([1-9]\d{0,10})"
RE_TOPIC_CHARSET = r"(?!\s)([a-z0-9 ğçıöşü&#()_+='%/\",.!?~\[\]{}<>^;\\|-]+)(?<!\s)"
"""Notice: Backtick ` is reserved."""

# For each new language append to these expressions.
SEE_EXPR = r"(?:bkz|see)"
SEARCH_EXPR = r"(?:ara|search)"
IMAGE_EXPR = r"(?:görsel|image)"

IMAGE_REGEX = fr"\({IMAGE_EXPR}: ([a-z0-9]{{8}})\)"

# Translators: Short for "also see this", used in entry editor.
SEE = pgettext_lazy("editor", "see")
SEARCH = pgettext_lazy("editor", "search")
IMAGE = pgettext_lazy("editor", "image")

# Translators: Entry date format. https://docs.djangoproject.com/en/3.0/ref/templates/builtins/#date
ENTRY_DATE_FORMAT = gettext_lazy("M j, Y")

# Translators: Entry time format. https://docs.djangoproject.com/en/3.0/ref/templates/builtins/#date
ENTRY_TIME_FORMAT = gettext_lazy("g:i a")


def q_unescape(string):
    """Convert *escaped* string fragment into valid URI."""
    return quote_plus(unescape(string))


def linkify(weburl_match):
    """Linkify given url. If the url is internal convert it to appropriate tag if possible."""
    domain, path = weburl_match.group(1), weburl_match.group(2) or ""

    if domain.endswith(settings.DOMAIN) and len(path) > 7:
        # Internal links (entries and topics)

        if permalink := re.match(r"^/entry/([0-9]+)/?$", path):
            return f'({SEE}: <a href="{path}">#{permalink.group(1)}</a>)'

        if topic := re.match(r"^/topic/([-a-zA-Z0-9]+)/?$", path):
            # Notice as we convert slug to title, this doesn't optimally translate
            # into original title, especially in non-English languages.
            slug = topic.group(1)
            guess = slug.replace("-", " ").strip()
            return f'({SEE}: <a href="{path}">{guess}</a>)'

        if image := re.match(r"^/img/([a-z0-9]{8})/?$", path):
            return f'<a role="button" tabindex="0" data-img="/img/{image.group(1)}" aria-expanded="false">{IMAGE}</a>'  # noqa

    path_repr = f"/...{path[-32:]}" if len(path) > 35 else path  # Shorten long urls
    url = domain + path

    return f'<a rel="ugc nofollow noopener" target="_blank" title="{url}" href="{url}">{domain}{path_repr}</a>'


@register.filter
def formatted(raw_entry):
    """
    Entry formatting/linkifying regex logic.
    """

    if not raw_entry:
        return ""

    entry = escape(raw_entry)  # Prevent XSS
    replacements = (
        # Reference
        (fr"\({SEE_EXPR}: #{RE_ENTRY_CHARSET}\)", fr'({SEE}: <a href="/entry/\1/">#\1</a>)'),
        (
            fr"\({SEE_EXPR}: (?!<)(@?{RE_TOPIC_CHARSET})\)",
            lambda m: fr'({SEE}: <a href="/topic/?q={q_unescape(m.group(1))}">{m.group(1)}</a>)',
        ),
        # Swh
        (
            fr"`:{RE_TOPIC_CHARSET}`",
            lambda m: fr'<a data-sup="({SEE}: {m.group(1)})" href="/topic/?q={q_unescape(m.group(1))}" title="({SEE}: {m.group(1)})">*</a>',  # noqa
        ),
        # Reference with no indicator
        (fr"`#{RE_ENTRY_CHARSET}`", r'<a href="/entry/\1/">#\1</a>'),
        (fr"`(@?{RE_TOPIC_CHARSET})`", lambda m: fr'<a href="/topic/?q={q_unescape(m.group(1))}">{m.group(1)}</a>'),
        # Search
        (
            fr"\({SEARCH_EXPR}: (@?{RE_TOPIC_CHARSET})\)",
            fr'({SEARCH}: <a data-keywords="\1" class="quicksearch" role="button" tabindex="0">\1</a>)',
        ),
        # Image
        (IMAGE_REGEX, fr'<a role="button" tabindex="0" data-img="/img/\1" aria-expanded="false">{IMAGE}</a>'),
        # Links. Order matters. In order to hinder clash between labelled and linkified:
        # Find links with label, then encapsulate them in anchor tag, which adds " character before the
        # link. Then we find all other links which don't have " at the start.
        # Users can't send " character, they send the escaped version: &quot;
        (
            fr"\[{RE_WEBURL} (?!\s|{RE_WEBURL_NC})([a-z0-9 ğçıöşü#&@()_+=':%/\",.!?*~`\[{{}}<>^;\\|-]+)(?<!\s)\]",
            r'<a rel="ugc nofollow noopener" target="_blank" href="\1\2">\3</a>',
        ),
        (fr"(?<!\"){RE_WEBURL}", linkify,),
    )

    for tag in replacements:
        entry = re.sub(*tag, entry)

    return mark_safe(entry)


@register.filter
def mark(formatted_entry, words):
    for word in sorted(words.split(), key=len, reverse=True):
        tag = (fr"({re.escape(escape(word))})(?!(.(?!<(a|mark)))*<\/(a|mark)>)", r"<mark>\1</mark>")
        formatted_entry = re.sub(*tag, formatted_entry)
    return mark_safe(formatted_entry)


@register.filter(expects_localtime=True)
def entrydate(created, edited):
    append = ""

    if edited is not None:
        edited = timezone.localtime(edited)

        if created.date() == edited.date():
            append = defaultfilters.date(edited, f" ~ {ENTRY_TIME_FORMAT}")
        else:
            append = defaultfilters.date(edited, f" ~ {ENTRY_DATE_FORMAT} {ENTRY_TIME_FORMAT}")

    return defaultfilters.date(created, f"{ENTRY_DATE_FORMAT} {ENTRY_TIME_FORMAT}") + append


@register.filter
def wished_by(topic, author):
    if not topic.exists:
        return False
    return topic.wishes.filter(author=author).exists()


@register.filter
def mediastamp(media_urls, mode):
    if mode not in ("regular", "today", "popular"):
        return ""

    has_instagram = False
    has_twitter = False

    media_set = tuple(dict.fromkeys(media_urls.split()))
    html = ""

    youtube = '<iframe class="border-0" width="100%" height="400" src="{}" \
     allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
    instagram = '<blockquote class="instagram-media w-100" data-instgrm-captioned data-instgrm-permalink="{}" \
     data-instgrm-version="12"></blockquote>'
    spotify = '<iframe class="border-0" src="{}" width="100%" height="{}" allowtransparency="true" \
     allow="encrypted-media"></iframe>'
    twitter = '<blockquote class="twitter-tweet" data-dnt="true"><a href="{}"></a></blockquote>'

    for url in filter(lambda u: not u.startswith("#"), map(escape, media_set)):
        if "youtube.com/embed/" in url:
            html += youtube.format(url)
        elif "instagram.com/p/" in url:
            html += instagram.format(url)
            has_instagram = True
        elif ("twitter.com/" in url) and ("/status/" in url):
            html += twitter.format(url)
            has_twitter = True
        elif "open.spotify.com/embed/" in url:
            if "/track/" in url:
                html += spotify.format(url, 80)
            else:
                html += spotify.format(url, 400)

    if has_instagram:
        html += '<script async src="//www.instagram.com/embed.js"></script>'

    if has_twitter:
        html += '<script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'

    return mark_safe(f'<section class="topic-media-area mt-2">{html}</section>')


@register.filter
def order_by(queryset, fields):
    return queryset.order_by(*fields.split())


@register.filter
def strdate(date_str):
    return parse(date_str)


@register.filter
def humanize_count(value):
    if not isinstance(value, int):
        return value
    # Translators: Short letter for "thousand", e.g. 1000 = 1.0k
    k = _("k")
    return f"{value / 1000:.1f}{k}" if value > 999 else str(value)
