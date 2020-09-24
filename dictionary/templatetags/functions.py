from django import template
from django.db.models import Exists, OuterRef
from django.utils.html import mark_safe
from django.utils.translation import gettext as _

from dictionary.conf import settings
from dictionary.models import Category, ExternalURL, Suggestion

register = template.Library()

"""
Make sure you restart the Django development
server every time you modify template tags.
"""


@register.simple_tag
def url_replace(request, field, value):
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.simple_tag
def firstofany(*args_list):
    for arg in args_list:
        if arg or arg == args_list[-1]:
            return arg
    return None


@register.simple_tag
def check_follow_status(user, topic):
    return topic.follow_check(user)


@register.simple_tag
def check_follow_user(user, target):
    return user.following.filter(pk=target.pk).exists()


@register.simple_tag
def has_perm(user, perm):
    return user.has_perm(perm)


@register.simple_tag
def get_external_urls():
    return ExternalURL.objects.all()


@register.simple_tag
def get_topic_suggestions(user, topic):
    def exists(direction):
        return Exists(Suggestion.objects.filter(direction=direction, author=user, topic=topic, category=OuterRef("pk")))

    return Category.objects_all.annotate(up=exists(1), down=exists(-1))


@register.simple_tag
def get_message_level(level):
    level_map = {40: "error", 30: "warning", 25: "success", 20: "info", 10: "debug"}
    return level_map.get(level, "warning")


@register.simple_tag(takes_context=True)
def print_topic_title(context):
    """Only for entry_list.html"""
    queries = context["request"].GET
    base = context["topic"].title

    if context["entry_permalink"]:
        return base + f" - #{context['entry_permalink'].pk}"

    mode_repr = {
        "today": _("today's entries"),
        "popular": _("popular"),
        "novices": _("novices"),
        "nice": _("most liked entries of all time"),
        "nicetoday": _("most liked entries of today"),
        "following": _("activity"),
        "recent": _("entries written after me"),
        "links": _("links"),
        "acquaintances": _("acquaintances"),
        "search": _("search: %(keywords)s") % {"keywords": queries.get("keywords", "")},
        "history": _("today in history: %(year)s") % {"year": queries.get("year", "")},
        "answered": _("entries with replies"),
        "images": _("images"),
    }

    if (mode := context["mode"]) in mode_repr:
        base += f" - {mode_repr[mode]}"

    if (page := context["page_obj"].number) > 1:
        base += " - " + _("page %(page)d") % {"page": page}

    return base


@register.simple_tag(takes_context=True)
def print_entry_class(context):
    entry = context["entry"]
    user = context["user"]
    classes = ["entry-full"]

    if user.is_authenticated:
        if entry.author == user:
            classes.append("owner")
        if entry.author.is_private:
            classes.append("private")
        if context.get("show_comments") and user.has_perm("dictionary.can_comment") and user.is_accessible:
            classes.append("commentable")

    if gap := context.get("gap"):
        classes.append(f"mb-{gap}")

    return mark_safe(f"class=\"{' '.join(classes)}\"")


@register.inclusion_tag("dictionary/includes/header_link.html", takes_context=True)
def render_header_link(context, slug):
    """
    Renders non-database header links (renders nothing if given category does not exist.)
    """

    details = settings.NON_DB_CATEGORIES_META.get(slug)

    if (slug in settings.LOGIN_REQUIRED_CATEGORIES and not context["user"].is_authenticated) or details is None:
        return {"unauthorized": True}

    frame = context.get("left_frame") or context.get("left_frame_fallback")
    is_active = slug == frame.slug if hasattr(frame, "slug") else False
    return {"hlink_slug": slug, "hlink_safename": details[0], "hlink_description": details[1], "is_active": is_active}
