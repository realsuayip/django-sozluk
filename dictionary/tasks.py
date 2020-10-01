from datetime import timedelta

from django.contrib.auth.models import Permission
from django.db.models import Count, Q

from djdict import celery_app

from dictionary.conf import settings
from dictionary.models import AccountTerminationQueue, Author, BackUp, GeneralReport, Image, UserVerification
from dictionary.utils import time_threshold


@celery_app.task
def process_backup(backup_id):
    BackUp.objects.get(id=backup_id).process()


# Periodic tasks


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    """Add and set intervals of periodic tasks."""
    sender.add_periodic_task(timedelta(hours=4), commit_user_deletions)
    sender.add_periodic_task(timedelta(hours=6), purge_images)
    sender.add_periodic_task(timedelta(hours=12), purge_verifications)
    sender.add_periodic_task(timedelta(hours=14), purge_reports)
    sender.add_periodic_task(timedelta(hours=16), grant_perm_suggestion)


@celery_app.task
def purge_verifications():
    """Delete expired verifications."""
    UserVerification.objects.filter(expiration_date__lte=time_threshold(hours=24)).delete()


@celery_app.task
def purge_reports():
    """Delete expired reports."""
    GeneralReport.objects.filter(is_verified=False, date_created__lte=time_threshold(hours=24)).delete()


@celery_app.task
def purge_images():
    """Delete expired images (Not bulk deleting so as to delete actual image files)."""
    expired = Image.objects.filter(is_deleted=True, date_created__lte=time_threshold(hours=120))
    for image in expired:
        image.delete()


@celery_app.task
def commit_user_deletions():
    """Delete (marked) users."""
    AccountTerminationQueue.objects.commit_terminations()


@celery_app.task
def grant_perm_suggestion():
    """Gives suitable users 'dictionary.can_suggest_categories' permission."""

    perm = Permission.objects.get(codename="can_suggest_categories")

    authors = (
        Author.objects_accessible.exclude(Q(user_permissions__in=[perm]) | Q(is_novice=True))
        .annotate(count=Count("entry", filter=Q(entry__is_draft=False)))
        .filter(count__gte=settings.SUGGESTIONS_ENTRY_REQUIREMENT)
    )

    for author in authors:
        author.user_permissions.add(perm)
