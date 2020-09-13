from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore as DBStore
from django.contrib.sessions.base_session import AbstractBaseSession
from django.db import models


User = get_user_model()


class PairedSession(AbstractBaseSession):
    # Custom session model which stores user foreignkey to associate sessions with particular users.
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    @classmethod
    def get_session_store_class(cls):
        return SessionStore


class SessionStore(DBStore):
    @classmethod
    def get_model_class(cls):
        return PairedSession

    def create_model_instance(self, data):
        obj = super().create_model_instance(data)

        try:
            user_id = int(data.get('_auth_user_id'))
            user = User.objects.get(pk=user_id)
        except (ValueError, TypeError, User.DoesNotExist):
            user = None
        obj.user = user
        return obj
