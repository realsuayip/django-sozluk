import random
import string

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...models import Author, Topic


class Command(BaseCommand):
    def handle(self, **options):
        if not settings.DEBUG:
            raise CommandError("This command is not allowed in production. Set DEBUG to False use this command.")

        size = int(input("size: "))
        while size > 0:
            chars = ''.join(random.sample(string.ascii_letters, 15))
            Topic.objects.create_topic(chars, Author.objects.get(pk=1))
            size -= 1
