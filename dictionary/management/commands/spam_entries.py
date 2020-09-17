import random

from django.utils import timezone

from dictionary.management.commands import BaseDebugCommand
from dictionary.models import Author, Entry, Topic

# spam random entries, by random users to (random) topics


class Command(BaseDebugCommand):
    def handle(self, **options):
        topics = None
        size = int(input("size: "))
        is_random = input("spam to specified topics? y/N: ")

        if is_random == "y":
            _range = input("pk range (x,y): ").split(",")
            topics = tuple(Topic.objects.filter(pk__range=(_range[0], _range[1])))

        while size > 0:
            topic = random.choice(topics) if topics is not None else Topic.objects.order_by("?").first()  # nosec
            author = Author.objects.filter(is_novice=False).order_by("?").first()
            Entry.objects.create(topic=topic, author=author, content=f"{topic}, {author}, {timezone.now()}")
            size -= 1
