import random
import string

from ...models import Author, Topic
from . import BaseDebugCommand


# spam random topics with random ascii letters, length of 15

class Command(BaseDebugCommand):
    def handle(self, **options):
        size = int(input("size: "))
        while size > 0:
            chars = ''.join(random.sample(string.ascii_letters, 15))  # nosec
            Topic.objects.create_topic(chars, Author.objects.get(pk=1))
            size -= 1
