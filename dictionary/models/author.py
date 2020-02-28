from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone

from ..utils import time_threshold
from ..utils.settings import PRIVATE_USERS
from .category import Category
from .entry import Entry


class AuthorNickValidator(UnicodeUsernameValidator):
    regex = r'^[a-z\ ]+$'
    message = "boşluk dışında türkçe ve özel karakter içermeyen alfabe harflerinden oluşan bir nick münasiptir"


class Author(AbstractUser):
    # Gender options
    MAN = 'MN'
    WOMAN = 'WM'
    OTHER = 'OT'
    UNKNOWN = 'NO'
    GENDERS = ((UNKNOWN, 'boşver'), (MAN, 'erkek'), (WOMAN, 'kadın'), (OTHER, 'diğer'))

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
        (PENDING, "çaylak listesinde"), (ON_HOLD, "entry girmesi bekleniyor"), (APPROVED, "yazar oldu"))

    # Recieving messages options
    DISABLED = "DS"
    ALL_USERS = "AU"
    AUTHOR_ONLY = "AO"
    FOLLOWING_ONLY = "FO"
    MESSAGE_PREFERENCE = ((DISABLED, "hiçkimse"), (ALL_USERS, "yazar ve çaylaklar"), (AUTHOR_ONLY, "yazarlar"),
                          (FOLLOWING_ONLY, "takip ettiklerim"))

    # Base auth related fields, notice: username field will be used for nicknames
    username = models.CharField('nick', max_length=35, unique=True,
                                help_text='şart. en fazla 35 karakter uzunluğunda, boşluk içerebilir özel ve türkçe '
                                          'karakter içeremez', validators=[AuthorNickValidator()],
                                error_messages={'unique': "bu nick kapılmış"})
    email = models.EmailField('e-posta adresi', unique=True)
    is_active = models.BooleanField(default=False, verbose_name="aktif")

    # Base auth field settings
    USERNAME_FIELD = 'email'

    # A list of the field names that will be prompted for when creating a user via the createsuperuser command.
    REQUIRED_FIELDS = ['username', 'is_active']

    # Novice application related fields
    is_novice = models.BooleanField(default=True, verbose_name="çaylak")
    application_status = models.CharField(max_length=2, choices=APPLICATION_STATUS, default=ON_HOLD)
    application_date = models.DateTimeField(null=True, blank=True, default=None)
    last_activity = models.DateTimeField(null=True, blank=True, default=None)

    # Suspension/termination details
    suspended_until = models.DateTimeField(null=True, blank=True, default=None)
    is_terminated = models.BooleanField(default=False, verbose_name="Hesap kapatıldı mı?")
    is_frozen = models.BooleanField(default=False, verbose_name="Hesap donuk mu?")

    # User-user relations
    following = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")
    blocked = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")

    # User-entry relations
    favorite_entries = models.ManyToManyField('Entry', through="EntryFavorites", related_name="favorited_by",
                                              blank=True)
    upvoted_entries = models.ManyToManyField('Entry', related_name="upvoted_by", blank=True)
    downvoted_entries = models.ManyToManyField('Entry', related_name="downvoted_by", blank=True)

    # User-category relations
    following_categories = models.ManyToManyField('Category', blank=True)

    # Personal info
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=2, choices=GENDERS, default=UNKNOWN)

    # Preferences
    entries_per_page = models.IntegerField(choices=ENTRY_COUNTS, default=TEN)
    topics_per_page = models.IntegerField(choices=TOPIC_COUNTS, default=FIFTY)
    message_preference = models.CharField(max_length=2, choices=MESSAGE_PREFERENCE, default=ALL_USERS)
    pinned_entry = models.OneToOneField('Entry', blank=True, null=True, on_delete=models.SET_NULL, related_name="+")

    def __str__(self):
        return f"{self.username}:{self.id}"

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        if created:
            # newly created user
            categories_list = list(Category.objects.all())
            self.following_categories.add(*categories_list)

    def get_absolute_url(self):
        return reverse("user-profile", kwargs={"username": self.username})

    class Meta:
        # Superusers need to have can_activate_user permission to accept a novice as an author.
        permissions = (("can_activate_user", "çaylak lisesine erişim"), ("suspend_user", "kullanıcıyı askıya alma"))
        verbose_name = "yazar"
        verbose_name_plural = "yazarlar"

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
        entry = Entry.objects_published.filter(author=self).order_by("-vote_rate").first()
        if entry and entry.vote_rate > Decimal("1"):
            return entry
        return None

    @property
    def email_confirmed(self):
        if self.userverification_set.filter(expiration_date__gte=time_threshold(hours=24)).exists():
            return False
        return True

    @property
    def is_suspended(self):
        if self.suspended_until and self.suspended_until > timezone.now():
            return True
        return False

    @property
    def is_private(self):
        return self.pk in PRIVATE_USERS


class EntryFavorites(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    entry = models.ForeignKey(Entry, on_delete=models.CASCADE)
    date_created = models.DateTimeField(null=True, blank=True, auto_now_add=True)

    def __str__(self):
        return self._meta.verbose_name + " #" + str(self.pk)

    class Meta:
        verbose_name = "Entry favorisi"
        verbose_name_plural = "Entry favorilenmeleri"


class Memento(models.Model):
    body = models.TextField(blank=True, null=True)
    holder = models.ForeignKey(Author, on_delete=models.CASCADE)
    patient = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=['holder', 'patient'], name='unique_memento')]

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
    NO_TRACE = 'NT'
    LEGACY = 'LE'
    LEGACY_ANONYMOUS = 'LA'
    FROZEN = 'FZ'
    STATES = ((NO_TRACE, 'hesabı komple sil'), (LEGACY, 'hesabı miras bırakarak sil'),
              (LEGACY_ANONYMOUS, 'hesabı anonim miras bırakarak sil'), (FROZEN, 'hesabı dondur'))

    author = models.OneToOneField(Author, on_delete=models.CASCADE)
    state = models.CharField(max_length=2, choices=STATES, default=FROZEN, verbose_name=" son sözünüz?")
    termination_date = models.DateTimeField(null=True, editable=False)
    date_created = models.DateTimeField(auto_now_add=True)

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
