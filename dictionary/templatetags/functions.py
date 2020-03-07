from django import template
from django.urls import reverse

from ..models import Entry
from ..utils.settings import FLATPAGE_URLS, LOGIN_REQUIRED_CATEGORIES, NON_DB_SLUGS_SAFENAMES, SOCIAL_URLS

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
def entry_full_url(req, entry_id):
    return req.build_absolute_uri(reverse('entry-permalink', kwargs={'entry_id': entry_id}))


@register.simple_tag
def check_follow_status(user, topic):
    return topic.follow_check(user)


@register.simple_tag
def check_category_follow_status(user, category):
    return category in user.following_categories.all()


@register.simple_tag
def url_flat(name):
    try:
        return Entry.objects.get(pk=FLATPAGE_URLS[name]).get_absolute_url()
    except Entry.DoesNotExist:
        return "/entry/1/"


@register.simple_tag
def url_social(name):
    return SOCIAL_URLS[name]


@register.inclusion_tag('dictionary/includes/header_link.html', takes_context=True)
def render_header_link(context, slug):
    """
    Renders non-database header links.
    """

    if slug in LOGIN_REQUIRED_CATEGORIES and not context['user'].is_authenticated:
        return {"unauthorized": True}

    details = NON_DB_SLUGS_SAFENAMES[slug]
    is_active = context['active_category'] == slug
    return {"hlink_slug": slug, "hlink_safename": details[0], "hlink_description": details[1], "is_active": is_active}
