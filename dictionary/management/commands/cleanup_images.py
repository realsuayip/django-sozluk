from django.core.management.base import BaseCommand

from ...models import Image
from ...utils import time_threshold


class Command(BaseCommand):
    """
    Delete expired images in database which have no longer use (5 days after
    the is_deleted mark). You need to set a cronjob for this command.
    """

    def handle(self, **options):
        # Notice: Bulk deletion wouldn't delete actual image files.
        expired = Image.objects.filter(is_deleted=True, date_created__lte=time_threshold(hours=120))
        for image in expired:
            image.delete()
