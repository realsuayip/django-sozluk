from uuslug import uuslug

from django.db import models
from django.db.models import Q

from .author import Author
from .category import Category
from .entry import Entry


class TopicFollowing(models.Model):
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic.id} => {self.author.username}"


class Topic(models.Model):
    title = models.CharField(max_length=50, unique=True)
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Author, on_delete=models.PROTECT)
    category = models.ManyToManyField(Category, blank=True)
    slug = models.SlugField(max_length=96, unique=True, blank=True)

    def save(self, *args, **kwargs):
        self.slug = uuslug(self.title, instance=self)
        super().save(*args, **kwargs)

    def has_entries(self):
        return Entry.objects_published.filter(topic=self).exists()  # used to be .count()

    def follow_check(self, user):
        return TopicFollowing.objects.filter(topic=self, author=user).exists()

    def latest_entry_date(self, sender):
        try:
            return Entry.objects.filter(topic=self).exclude(
                Q(author__in=sender.blocked.all()) | Q(author=sender)).latest("date_created").date_created
        except Entry.DoesNotExist:
            return self.date_created

    def __str__(self):
        return f"{self.title}"
