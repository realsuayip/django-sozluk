from django.core.management.base import BaseCommand
from dictionary.models import Author, Entry, Topic
import random


# spam random entries, by random users to random topics


class Command(BaseCommand):
    def handle(self, **options):
        size = int(input("size: "))
        while size > 0:
            topic = Topic.objects.order_by("?").first()
            author = Author.objects.filter(is_novice=False).order_by("?").first()
            Entry.objects.create(topic=topic, author=author, content=f"{topic}, {author}, {random.randint(1, 999)}")
            size -= 1
