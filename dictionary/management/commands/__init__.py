from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class BaseDebugCommand(BaseCommand):
    def __init__(self, *args, **kwargs):
        if not settings.DEBUG:
            raise CommandError("This command is not allowed in production. Set DEBUG to False to use this command.")

        super().__init__(*args, **kwargs)

    def handle(self, *args, **options):
        raise NotImplementedError("Provide a handle() method yourself!")
