from django.core.validators import RegexValidator, MaxLengthValidator
from django.db import models
from django.db.models import Q

from uuslug import uuslug

from .author import Author
from .category import Category
from .entry import Entry
from .managers.topic import TopicManager, TopicManagerPublished
from ..utils import turkish_lower

TOPIC_TITLE_VALIDATORS = [RegexValidator(r"""^[a-z0-9 ğçıöşü#₺&@()_+=':%/"*,.!?~\[\] {} <>^;\\|-]+$""",
                                         message="bu başlık geçerisz karakterler içeriyor"),
                          MaxLengthValidator(50, message="bu başlık çok uzun")]


class TopicFollowing(models.Model):
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="followers")
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic.id} => {self.author.username}"


class Topic(models.Model):
    title = models.CharField(max_length=50, unique=True, validators=TOPIC_TITLE_VALIDATORS)
    date_created = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Author, null=True, blank=True, on_delete=models.SET_NULL)
    category = models.ManyToManyField(Category, blank=True)
    slug = models.SlugField(max_length=96, unique=True, blank=True)

    objects = TopicManager()
    objects_published = TopicManagerPublished()

    def save(self, *args, **kwargs):
        self.title = turkish_lower(self.title)
        self.slug = uuslug(self.title, instance=self)
        super().save(*args, **kwargs)

    def follow_check(self, user):
        return TopicFollowing.objects.filter(topic=self, author=user).exists()

    def latest_entry_date(self, sender):
        try:
            return Entry.objects.filter(topic=self).exclude(
                Q(author__in=sender.blocked.all()) | Q(author=sender)).latest("date_created").date_created
        except Entry.DoesNotExist:
            return self.date_created

    @property
    def exists(self):
        return True

    @property
    def has_entries(self):
        return self.entries.exclude(is_draft=True).exists()

    def __str__(self):
        return f"{self.title}"
