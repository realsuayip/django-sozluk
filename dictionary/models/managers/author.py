import logging

from django.contrib.auth.models import UserManager
from django.db import models
from django.db.models import BooleanField, Case, Q, When
from django.utils import timezone

from dictionary.utils import get_generic_privateuser, time_threshold


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


class InNoviceList(AuthorManagerAccessible):
    def get_queryset(self):
        return super().get_queryset().filter(is_novice=True, application_status="PN")

    def get_ordered(self, limit=None):
        """Return all users in novice list, ordered."""
        qs = self.annotate_activity(self.filter(last_activity__isnull=False)).order_by(
            "-queue_priority", "-is_active_today", "application_date"
        )
        if limit is not None:
            return qs[:limit]
        return qs

    @staticmethod
    def annotate_activity(queryset):
        return queryset.annotate(
            is_active_today=Case(
                When(Q(last_activity__gte=time_threshold(hours=24)), then=True),
                default=False,
                output_field=BooleanField(),
            )
        )


class AccountTerminationQueueManager(models.Manager):
    _private_user = None

    def get_terminated(self):
        return self.exclude(state="FZ").filter(termination_date__lt=timezone.now())

    @staticmethod
    def terminate_no_trace(user):
        logger.info("User account terminated: %s<->%d", user.username, user.pk)
        user.delete()

    def terminate_legacy(self, user):
        if not user.is_novice:
            # Migrate entries before deleting the user completely
            user.entry_set(manager="objects_published").all().update(author=self._private_user)
            logger.info("User entries migrated: %s<->%d", user.username, user.pk)

        self.terminate_no_trace(user)

    def commit_terminations(self):
        self._private_user = get_generic_privateuser()

        for termination in self.get_terminated().select_related("author"):
            if termination.state == "NT":
                self.terminate_no_trace(termination.author)
            elif termination.state == "LE":
                self.terminate_legacy(termination.author)
