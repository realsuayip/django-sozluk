from django.core.management.base import BaseCommand

from ...models import GeneralReport, UserVerification
from ...utils import time_threshold


class Command(BaseCommand):
    """
    Delete expired objects in database which have no longer use. You may want to set a cronjob for this command.
    todo: Add some logging
    """

    def handle(self, **options):
        # Delete expired userverification objects
        expired = UserVerification.objects.filter(expiration_date__lte=time_threshold(hours=24))
        expired.delete()

        # Delete expired/unverified reports
        unverified = GeneralReport.objects.filter(is_verified=False, date_created__lte=time_threshold(hours=24))
        unverified.delete()
