from django import template

from ..models import ExternalURL
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
def get_external_urls():
    return ExternalURL.objects.all()


@register.simple_tag
def get_message_level(level):
    level_map = {40: "error", 30: "warning", 25: "success", 20: "info", 10: "debug"}
    return level_map.get(level, "warning")


@register.inclusion_tag("dictionary/includes/header_link.html", takes_context=True)
def render_header_link(context, slug):
    """
    Renders non-database header links.
    """

    if slug in LOGIN_REQUIRED_CATEGORIES and not context["user"].is_authenticated:
        return {"unauthorized": True}

    details = NON_DB_CATEGORIES_META[slug]
    is_active = context.get("left_frame", {}).get("slug") == slug
    return {"hlink_slug": slug, "hlink_safename": details[0], "hlink_description": details[1], "is_active": is_active}
