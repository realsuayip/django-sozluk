from .models import TopicFollowing
from django.utils import timezone
from .utils.settings import ENTRIES_PER_PAGE

# this file will be moved


def get_current_path(request):
    return {'current_path': request.get_full_path()}


def find_after_page(pages_before):
    is_on = pages_before + 1
    page_count = 0
    while is_on > 0:
        page_count += 1
        is_on -= ENTRIES_PER_PAGE
    if is_on == 0:
        page_count += 1
    return page_count


def mark_read(topic, user):
    """
    Marks the topic read, if user is following it.
    """
    try:
        obj = TopicFollowing.objects.get(topic=topic, author=user)
    except TopicFollowing.DoesNotExist:
        return False
    obj.read_at = timezone.now()
    obj.save()
    return True
