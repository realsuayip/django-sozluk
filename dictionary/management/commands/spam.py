from django.core.management.base import BaseCommand
from dictionary.models import Author, Entry, Topic
import random

# spam random entries, by random users to random topics


class Command(BaseCommand):
    def handle(self, **options):
        size = int(input("size: "))
        while size > 0:
            topic_id, *_ = random.choice(Topic.objects.values_list("id"))
            author_id, *_ = random.choice(Author.objects.filter(is_novice=False).values_list("id"))
            Entry.objects.create(topic=Topic.objects.get(id=topic_id), author=Author.objects.get(id=author_id),
                                 content=f"{topic_id}, {author_id}, {random.randint(1, 999)}")
            size -= 1
