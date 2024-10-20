from django.contrib.auth.hashers import make_password
from django.core.management import call_command
from django.core.management.base import BaseCommand

from dictionary.conf import settings
from dictionary.models import Author


class Command(BaseCommand):
    def handle(self, **options):
        call_command("migrate")
        call_command("collectstatic", "--noinput")

        attrs = {
            "is_active": True,
            "is_novice": False,
            "application_status": Author.Status.APPROVED,
            "message_preference": Author.MessagePref.DISABLED,
            "password": make_password(None),
        }
        Author.objects.get_or_create(
            username=settings.GENERIC_PRIVATEUSER_USERNAME,
            defaults={
                **attrs,
                "email": "private@%s" % settings.DOMAIN,
                "is_private": True,
            },
        )
        Author.objects.get_or_create(
            username=settings.GENERIC_SUPERUSER_USERNAME,
            defaults={
                **attrs,
                "email": "generic@%s" % settings.DOMAIN,
                "is_private": False,
            },
        )
