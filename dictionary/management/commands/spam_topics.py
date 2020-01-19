import random
import string

from django.core.management.base import BaseCommand

from ...models import Author, Topic


class Command(BaseCommand):
    def handle(self, **options):
        size = int(input("size: "))
        while size > 0:
            chars = ''.join(random.sample(string.ascii_letters, 15))
            Topic.objects.create_topic(chars, Author.objects.get(pk=1))
            size -= 1
