import logging

from django.contrib.auth.models import UserManager
from django.db.models import Q
from django.db import models
from django.utils import timezone

from ...utils import get_generic_privateuser


logger = logging.getLogger(__name__)


class AuthorManagerAccessible(UserManager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .exclude(
                Q(is_frozen=True) | Q(is_private=True) | Q(is_active=False) | Q(suspended_until__gt=timezone.now())
            )
        )


class AccountTerminationQueueManager(models.Manager):
    def get_terminated(self):
        return self.exclude(state="FZ").filter(termination_date__lt=timezone.now())

    @staticmethod
    def terminate_no_trace(user):
        logger.info("User account terminated: %s<->%d", user.username, user.pk)
        user.delete()

    def terminate_legacy(self, user):
        if not user.is_novice:
            # Migrate entries before deleting the user completely
            user.entry_set.all().update(author=get_generic_privateuser())
            logger.info("User entires migrated: %s<->%d", user.username, user.pk)

        self.terminate_no_trace(user)

    def commit_terminations(self):
        for termination in self.get_terminated():
            if termination.state == "NT":
                self.terminate_no_trace(termination.author)
            elif termination.state == "LE":
                self.terminate_legacy(termination.author)
