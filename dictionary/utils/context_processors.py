from ..models import Category, Conversation, TopicFollowing
from django.core.exceptions import ObjectDoesNotExist


def header_categories(request):
    """
    Required for header category navigation.
    """
    return dict(nav_categories=Category.objects.all())


def message_status(request):
    """
    Checks if any unread messages exists, enables the indicator in the header if there are.
    """
    unread_message_status = False

    if request.user.is_authenticated:
        try:
            for chat in Conversation.objects.list_for_user(request.user):
                if chat.last_message.recipient == request.user and not chat.last_message.read_at:
                    unread_message_status = True
                    break
        except Conversation.DoesNotExist:
            pass

    return dict(user_has_unread_messages=unread_message_status)


def following_status(request):
    """
    Enables the indicator in the header, if there is new content from following topics.
    Notice: only for following topics, not users. there is a dedicated tab named "son" in header for that.
    """
    status = False
    if request.user.is_authenticated:
        user_following = TopicFollowing.objects.filter(author=request.user)

        try:
            for following in user_following:
                if following.read_at < following.topic.latest_entry_date(request.user):
                    status = True
                    break
        except ObjectDoesNotExist:
            pass
    return dict(user_has_unread_followings=status)
