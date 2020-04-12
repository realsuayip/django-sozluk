import math
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models import BooleanField, Case, F, Max, Q, When
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from uuslug import uuslug

from ..utils import parse_date_or_none, time_threshold
from ..utils.settings import DISABLE_GENERATIONS, FIRST_GENERATION_DATE, GENERATION_GAP_DAYS
from .category import Category
from .entry import Entry
from .managers.author import AccountTerminationQueueManager


class AuthorNickValidator(UnicodeUsernameValidator):
    regex = r"^[a-z\ ]+$"
    message = "boşluk dışında türkçe ve özel karakter içermeyen alfabe harflerinden oluşan bir nick münasiptir"


class Author(AbstractUser):
    # Gender options
    MAN = "MN"
    WOMAN = "WM"
    OTHER = "OT"
    UNKNOWN = "NO"
    GENDERS = ((UNKNOWN, "boşver"), (MAN, "erkek"), (WOMAN, "kadın"), (OTHER, "diğer"))

    # Entry/topic per page preference options
    TEN = 10
    THIRTY = 30
    FIFTY = 50
    SEVENTYFIVE = 75
    ONEHUNDRED = 100
    ENTRY_COUNTS = ((TEN, "10"), (THIRTY, "30"), (FIFTY, "50"), (ONEHUNDRED, "100"))
    TOPIC_COUNTS = ((THIRTY, "30"), (FIFTY, "50"), (SEVENTYFIVE, "75"), (ONEHUNDRED, "100"))

    # Status of author queue
    PENDING = "PN"
    ON_HOLD = "OH"
    APPROVED = "AP"
    APPLICATION_STATUS = (
        (PENDING, "çaylak listesinde"),
        (ON_HOLD, "entry girmesi bekleniyor"),
        (APPROVED, "yazar oldu"),
    )

    # Recieving messages options
    DISABLED = "DS"
    ALL_USERS = "AU"
    AUTHOR_ONLY = "AO"
    FOLLOWING_ONLY = "FO"
    MESSAGE_PREFERENCE = (
        (DISABLED, "hiçkimse"),
        (ALL_USERS, "yazar ve çaylaklar"),
        (AUTHOR_ONLY, "yazarlar"),
        (FOLLOWING_ONLY, "takip ettiklerim"),
    )

    # Base auth related fields, notice: username field will be used for nicknames
    username = models.CharField(
        "nick",
        max_length=35,
        unique=True,
        help_text="şart. en fazla 35 karakter uzunluğunda, boşluk içerebilir özel ve türkçe karakter içeremez",
        validators=[AuthorNickValidator()],
        error_messages={"unique": "bu nick kapılmış"},
    )

    slug = models.SlugField(max_length=35, unique=True, editable=False)
    email = models.EmailField("e-posta adresi", unique=True)
    is_active = models.BooleanField(default=False, verbose_name="aktif")

    # Base auth field settings
    USERNAME_FIELD = "email"

    # A list of the field names that will be prompted for when creating a user via the createsuperuser command.
    REQUIRED_FIELDS = ["username", "is_active"]

    # Novice application related fields
    is_novice = models.BooleanField(default=True, verbose_name="çaylak")
    application_status = models.CharField(max_length=2, choices=APPLICATION_STATUS, default=ON_HOLD)
    application_date = models.DateTimeField(null=True, blank=True, default=None)
    last_activity = models.DateTimeField(null=True, blank=True, default=None)

    # Accessibility details
    suspended_until = models.DateTimeField(null=True, blank=True, default=None)
    is_frozen = models.BooleanField(default=False, verbose_name="Hesap donuk mu?")
    is_private = models.BooleanField(default=False, verbose_name="Hesap anonim mi?")

    # User-user relations
    following = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")
    blocked = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")

    # User-entry relations
    favorite_entries = models.ManyToManyField(
        "Entry", through="EntryFavorites", related_name="favorited_by", blank=True
    )
    upvoted_entries = models.ManyToManyField("Entry", related_name="upvoted_by", blank=True)
    downvoted_entries = models.ManyToManyField("Entry", related_name="downvoted_by", blank=True)

    # User-category relations
    following_categories = models.ManyToManyField("Category", blank=True)

    # User-topic relations
    following_topics = models.ManyToManyField("Topic", through="TopicFollowing", related_name="followers", blank=True)

    # Personal info
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=2, choices=GENDERS, default=UNKNOWN)

    # Preferences
    entries_per_page = models.IntegerField(choices=ENTRY_COUNTS, default=TEN)
    topics_per_page = models.IntegerField(choices=TOPIC_COUNTS, default=FIFTY)
    message_preference = models.CharField(max_length=2, choices=MESSAGE_PREFERENCE, default=ALL_USERS)
    pinned_entry = models.OneToOneField("Entry", blank=True, null=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"{self.username}:{self.id}"

    class Meta:
        # Superusers need to have can_activate_user permission to accept a novice as an author.
        permissions = (("can_activate_user", "çaylak lisesine erişim"), ("suspend_user", "kullanıcıyı askıya alma"))
        verbose_name = "yazar"
        verbose_name_plural = "yazarlar"

    def save(self, *args, **kwargs):
        created = self.pk is None  # If True, the user is created (not updated).

        if created:
            self.slug = uuslug(self.username, instance=self)

        super().save(*args, **kwargs)

        if created:
            self.following_categories.add(*Category.objects.all())

    def delete(self, *args, **kwargs):
        # Delete related conversations before deleting messages (via self.delete())
        apps.get_model("dictionary", "Conversation").objects.filter(participants__in=[self]).delete()
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("user-profile", kwargs={"slug": self.slug})

    @property
    def generation(self):
        if DISABLE_GENERATIONS:
            return None

        gen_start_date = parse_date_or_none(FIRST_GENERATION_DATE)

        if gen_start_date is None:
            raise ValueError("Invalid configuration for 'FIRST_GENERATION_DATE'. Please provide a valid date.")

        delta = self.date_joined - gen_start_date
        return math.ceil((delta.days / GENERATION_GAP_DAYS) or 1)

    @property
    def entry_count(self):
        return Entry.objects_published.filter(author=self).count()

    @property
    def entry_count_month(self):
        return Entry.objects_published.filter(author=self, date_created__gte=time_threshold(days=30)).count()

    @property
    def entry_count_week(self):
        return Entry.objects_published.filter(author=self, date_created__gte=time_threshold(days=7)).count()

    @property
    def entry_count_day(self):
        return Entry.objects_published.filter(author=self, date_created__gte=time_threshold(days=1)).count()

    @property
    def last_entry_date(self):
        try:
            return Entry.objects_published.filter(author=self).latest("date_created").date_created
        except Entry.DoesNotExist:
            return None

    @property
    def followers(self):
        return Author.objects.filter(following=self)

    @property
    def entry_nice(self):
        return Entry.objects_published.filter(author=self, vote_rate__gt=Decimal("1")).order_by("-vote_rate").first()

    @property
    def email_confirmed(self):
        return not self.userverification_set.filter(expiration_date__gte=time_threshold(hours=24)).exists()

    @property
    def is_suspended(self):
        return self.suspended_until is not None and self.suspended_until > timezone.now()

    @cached_property
    def has_unread_messages(self):
        return apps.get_model("dictionary", "Message").objects.filter(recipient=self, read_at__isnull=True).exists()

    @cached_property
    def has_unread_topics(self):
        queryset = self.following_topics.annotate(
            latest=Max("entries__date_created", filter=~Q(entries__author=self)),
            is_read=Case(
                When(Q(latest__gt=F("topicfollowing__read_at")), then=False), default=True, output_field=BooleanField()
            ),
        ).filter(is_read=False)
        return queryset.exists()


class Memento(models.Model):
    body = models.TextField(blank=True, null=True)
    holder = models.ForeignKey(Author, on_delete=models.CASCADE)
    patient = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["holder", "patient"], name="unique_memento")]

    def __str__(self):
        return f"{self.__class__.__name__}#{self.id}, from {self.holder} about {self.patient}"


class UserVerification(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    verification_token = models.CharField(max_length=128)
    new_email = models.EmailField(null=True, blank=True)  # new e-mail if it is subject to change
    expiration_date = models.DateTimeField()

    def save(self, *args, **kwargs):
        UserVerification.objects.filter(author=self.author).delete()
        super().save(*args, **kwargs)


class AccountTerminationQueue(models.Model):
    NO_TRACE = "NT"
    LEGACY = "LE"
    FROZEN = "FZ"
    STATES = ((NO_TRACE, "hesabı komple sil"), (LEGACY, "hesabı miras bırakarak sil"), (FROZEN, "hesabı dondur"))

    author = models.OneToOneField(Author, on_delete=models.CASCADE)
    state = models.CharField(max_length=2, choices=STATES, default=FROZEN, verbose_name=" son sözünüz?")
    termination_date = models.DateTimeField(null=True, editable=False)
    date_created = models.DateTimeField(auto_now_add=True)

    objects = AccountTerminationQueueManager()

    def __str__(self):
        return f"{self.author}, status={self.state} to be terminated after: {self.termination_date or 'N/A'}"

    def save(self, *args, **kwargs):
        created = self.pk is None

        if created:
            self.author.is_frozen = True
            self.author.save()

            if self.state != self.FROZEN:
                self.termination_date = timezone.now() + timezone.timedelta(hours=120)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.author.is_frozen = False
        self.author.save()
        super().delete(*args, **kwargs)
