from django.utils import timezone

from ...models import Author, Entry, Topic
from . import BaseDebugCommand


# spam random entries, by random users to random topics


class Command(BaseDebugCommand):
    def handle(self, **options):
        size = int(input("size: "))
        while size > 0:
            topic = Topic.objects.order_by("?").first()
            author = Author.objects.filter(is_novice=False).order_by("?").first()
            Entry.objects.create(topic=topic, author=author, content=f"{topic}, {author}, {timezone.now()}")
            size -= 1
