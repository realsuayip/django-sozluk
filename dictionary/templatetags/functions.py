from django import template
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db import connection
from django.utils.html import mark_safe

from ..models import ExternalURL, Topic
from ..utils.settings import LOGIN_REQUIRED_CATEGORIES, NON_DB_CATEGORIES_META


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
def check_follow_status(user, topic):
    return topic.follow_check(user)


@register.simple_tag
def check_follow_user(user, target):
    return user.following.filter(pk=target.pk).exists()


@register.simple_tag
def get_external_urls():
    return ExternalURL.objects.all()


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
        "today": "bugün girilen entry'ler",
        "popular": "gündem",
        "novices": "çaylaklar",
        "nice": "şükela tümü",
        "nicetoday": "şükela bugün",
        "following": "olan biten",
        "recent": "benden sonra girilenler",
        "links": "linkler",
        "acquaintances": "takip ettiklerim",
        "search": f"arama: {queries.get('keywords', '')}",
        "history": f"tarihte bugün: {queries.get('year', '')}",
    }

    if (mode := context["mode"]) in mode_repr:
        base += f" - {mode_repr[mode]}"

    if (page := context["page_obj"].number) > 1:
        base += f" - sayfa {page}"

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
    Renders non-database header links. (Renders nothing if the given cateogry does not exist.)
    """

    details = NON_DB_CATEGORIES_META.get(slug)

    if (slug in LOGIN_REQUIRED_CATEGORIES and not context["user"].is_authenticated) or details is None:
        return {"unauthorized": True}

    is_active = context.get("left_frame", {}).get("slug") == slug
    return {"hlink_slug": slug, "hlink_safename": details[0], "hlink_description": details[1], "is_active": is_active}


@register.inclusion_tag("dictionary/includes/topic_suggestions.html")
def render_topic_suggestions(title):
    suggestions = None

    if connection.vendor == "postgresql":
        suggestions = tuple(
            Topic.objects_published.annotate(
                rank=SearchRank(SearchVector("title", weight="A"), SearchQuery(title), weights=[0.3, 0.4, 0.5, 0.6])
            )
            .filter(rank__gte=0.4)
            .order_by("-rank")[:5]
        )

    return {"suggestions": suggestions}
