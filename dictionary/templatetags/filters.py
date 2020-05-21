import re

from django import template
from django.template import defaultfilters
from django.utils import timezone
from django.utils.html import escape, mark_safe

from ..utils import RE_WEBURL
from ..utils.settings import DOMAIN


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
    7) Input: `@username` Output: @username -- A link that points to the user profile
    8) Input: (ara: beni yar) Output: unchanged, but 'beni yar' has a link that, when clicked searchs for that keyword
    in topics and appends to the left frame (redirects to the advanced search page on mobile). Same rules of (2)
    9) Input http://www.djangoproject.com  Output: http://www.djangoproject.com  -- Linkification. (protocol required)
    10) Input: [http://www.djangoproject.com django] Output: django -- A link that opens http://www.djangoproject.com in
    a new tab. Protocol name (http/https only) required. Rules for text is the same as (2)
    """

    if not raw_entry:
        return ""

    def linkify(weburl_match):
        """Linkify given url. If the url is internal convert it to appropriate tag if possible."""
        domain, path = weburl_match.group(1), weburl_match.group(2) or ""

        if domain.endswith(DOMAIN) and len(path) > 7:
            # Internal links (entries and topics)

            if (permalink := re.match(r"^/entry/([0-9]+)/?$", path)) is not None:
                return f'(bkz: <a href="{path}">#{permalink.group(1)}</a>)'

            if (topic := re.match(r"^/topic/([-a-zA-Z0-9]+)/?$", path)) is not None:
                # todo: When topic auto-redirect feature gets implemented, add redirect flag to this url.
                slug = topic.group(1)
                guess = slug.replace("-", " ").strip()
                return f'(bkz: <a href="{path}">{guess}</a>)'

        path_repr = f"/...{path[-32:]}" if len(path) > 35 else path  # Shorten long urls
        url = domain + path

        return f'<a rel="nofollow noopener" target="_blank" title="{url}" href="{url}">{domain}{path_repr}</a>'

    entry = escape(raw_entry)  # Prevent XSS
    replacements = (
        (r"\(bkz: #([1-9]\d{0,10})\)", r'(bkz: <a href="/entry/\1">#\1</a>)'),
        (r"\(bkz: (?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)\)", r'(bkz: <a href="/topic/?q=\1">\1</a>)'),
        (r"\(bkz: @(?!\s)([a-z0-9]+(\ [a-z0-9]+)*)(?<!\s)\)", r'(bkz: <a href="/biri/\1/">@\1</a>)'),
        (
            r"`:(?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)`",
            r'<a data-sup="(bkz: \1)" href="/topic/?q=\1" title="(bkz: \1)">*</a>',
        ),
        (r"`#([1-9]\d{0,10})`", r'<a href="/entry/\1">#\1</a>'),
        (r"`(?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)`", r'<a href="/topic/?q=\1">\1</a>'),
        (r"`@(?!\s)([a-z0-9]+(\ [a-z0-9]+)*)(?<!\s)`", r'<a href="/biri/\1/">@\1</a>'),
        (
            r"\(ara: (?!\s)(@?[a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)\)",
            r'(ara: <a data-keywords="\1" class="quicksearch" role="button" tabindex="0">\1</a>)',
        ),
        # Order matters. In order to hinder clash between labelled and linkified:
        # Find links with label, then encapsulate them in anchor tag, which adds " character before the
        # link. Then we find all other links which don't have " at the start.
        # Users can't send " character, they send the escaped version: &quot;
        (
            fr"\[{RE_WEBURL} (?!\s)([a-zA-Z0-9 ğüşöçıİĞÜŞÖÇ]+)(?<!\s)\]",
            r'<a rel="nofollow noopener" target="_blank" href="\1\2">\3</a>',
        ),
        (fr"(?<!\"){RE_WEBURL}", linkify,),
    )

    for tag in replacements:
        entry = re.sub(*tag, entry)

    return mark_safe(entry)


@register.filter(expects_localtime=True)
def entrydate(created, edited):
    append = ""

    if edited is not None:
        edited = timezone.localtime(edited)

        if created.date() == edited.date():
            append = defaultfilters.date(edited, " ~ H:i")
        else:
            append = defaultfilters.date(edited, " ~ d.m.Y H:i")

    return defaultfilters.date(created, "d.m.Y H:i") + append


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
    media_set = tuple(dict.fromkeys(media_urls.split()))
    html = ""

    youtube = '<iframe class="border-0" width="100%" height="400" src="{}" \
     allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>'
    instagram = '<blockquote class="instagram-media w-100" data-instgrm-captioned data-instgrm-permalink="{}" \
     data-instgrm-version="12"></blockquote>'
    spotify = '<iframe class="border-0" src="{}" width="100%" height="{}" allowtransparency="true" \
     allow="encrypted-media"></iframe>'

    for url in filter(lambda u: not u.startswith("#"), map(escape, media_set)):
        if "youtube.com/embed/" in url:
            html += youtube.format(url)
        elif "instagram.com/p/" in url:
            html += instagram.format(url)
            has_instagram = True
        elif "open.spotify.com/embed/" in url:
            if "/track/" in url:
                html += spotify.format(url, 80)
            else:
                html += spotify.format(url, 400)

    if has_instagram:
        html = '<script async src="//www.instagram.com/embed.js"></script>' + html

    return mark_safe(f'<section class="topic-media-area mt-2">{html}</section>')
