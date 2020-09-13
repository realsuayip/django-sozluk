from django.conf import settings
from django.core.cache import cache

from .cached_db import KEY_PREFIX, __name__ as cached_db_name
from .db import PairedSession


def flush_all_sessions(user):
    """Invalidate ALL sessions of a user."""

    sessions = PairedSession.objects.filter(user=user)
    cached = settings.SESSION_ENGINE == cached_db_name

    for session in sessions:
        if cached:
            cache_key = KEY_PREFIX + session.session_key  # Determined in DjangoCachedDBStore
            cache.delete(cache_key)

        session.delete()
