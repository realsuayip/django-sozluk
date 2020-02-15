from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...models import Author, Entry, Topic


# spam random entries, by random users to random topics


class Command(BaseCommand):
    def handle(self, **options):
        if not settings.DEBUG:
            raise CommandError("This command is not allowed in production. Set DEBUG to False use this command.")

        size = int(input("size: "))
        while size > 0:
            topic = Topic.objects.order_by("?").first()
            author = Author.objects.filter(is_novice=False).order_by("?").first()
            Entry.objects.create(topic=topic, author=author, content=f"{topic}, {author}, {timezone.now()}")
            size -= 1
