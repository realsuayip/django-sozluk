from django.contrib.sessions.backends.cached_db import SessionStore as DjangoCachedDBStore


from .db import SessionStore as DictionarySessionStore


KEY_PREFIX = "dictionary.cached_session"


class SessionStore(DictionarySessionStore, DjangoCachedDBStore):
    """
    Makes database sessions use cache. Implementation inspired by:
    https://github.com/QueraTeam/django-qsessions
    """

    cache_key_prefix = KEY_PREFIX
