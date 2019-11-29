from django import template
from django.core.exceptions import ObjectDoesNotExist
from ..models import Category, Conversation, TopicFollowing, Entry

register = template.Library()

"""
Make sure you restart the Django development
server every time you modify template tags.
"""


@register.simple_tag
def categories_list():
    """
    Required for header category navigation.
    """
    return Category.objects.all()


@register.simple_tag
def message_status(user, unread_count=False):
    """
    Checks if any unread messages exists, enables the indicator in the header if there are.
    """
    unread_message_exists = False
    unread_message_count = 0

    try:
        for chat in Conversation.objects.list_for_user(user):
            if chat.last_message.recipient == user and not chat.last_message.read_at:
                unread_message_exists = True
                unread_message_count += 1
    except ObjectDoesNotExist:
        return 0

    if unread_count:
        return unread_message_count
    else:
        return unread_message_exists


@register.simple_tag
def following_status(user):
    """
    Enables the indicator in the header, if there is new content from following topics.
    Notice: only for following topics, not users. there is a dedicated tab named "son" in header for that.
    """
    user_following = TopicFollowing.objects.filter(author=user)
    try:
        for following in user_following:
            if following.read_at < following.topic.latest_entry_date(user):
                return True
    except (Entry.DoesNotExist, TopicFollowing.DoesNotExist):  # couln't find any objects
        return False
    return False  # found objects but they didn't pass the condition
