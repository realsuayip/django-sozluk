from django.core.management.base import BaseCommand

from ...models import AccountTerminationQueue


class Command(BaseCommand):
    """
    Delete/modify user accounts that are selected to be terminated. Set a cronjob (every 2-3 hours) for this command to
    regularly terminate accounts. Be sure to set GENERIC_PRIVATEUSER_USERNAME properly.
    """

    def handle(self, **options):
        AccountTerminationQueue.objects.commit_terminations()
