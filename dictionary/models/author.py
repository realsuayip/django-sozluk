import math

from contextlib import suppress
from decimal import Decimal

from django.apps import apps
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import BooleanField, Case, Count, F, Q, Sum, When
from django.db.models.functions import Coalesce
from django.shortcuts import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _

from uuslug import uuslug

from ..models.m2m import DownvotedEntries, UpvotedEntries
from ..utils import get_generic_superuser, parse_date_or_none, time_threshold
from ..utils.settings import (
    DAILY_VOTE_LIMIT,
    DAILY_VOTE_LIMIT_PER_USER,
    DISABLE_GENERATIONS,
    FIRST_GENERATION_DATE,
    GENERATION_GAP_DAYS,
    KARMA_BOUNDARY_LOWER,
    KARMA_BOUNDARY_UPPER,
    KARMA_EXPRESSIONS,
    OVERWHELMING_KARMA_EXPRESSION,
    TOTAL_VOTE_LIMIT_PER_USER,
    UNDERWHELMING_KARMA_EXPRESSION,
)
from ..utils.validators import validate_username_partial
from .category import Category
from .managers.author import AccountTerminationQueueManager, AuthorManagerAccessible, InNoviceList


class AuthorNickValidator(UnicodeUsernameValidator):
    regex = r"^[a-z0-9]+(\ [a-z0-9]+)*$"
    message = _("unlike what you sent, an appropriate nickname would only consist of letters, numbers and spaces.")


class Author(AbstractUser):
    # Gender options
    MAN = "MN"
    WOMAN = "WM"
    OTHER = "OT"
    UNKNOWN = "NO"
    GENDERS = ((UNKNOWN, _("forget it")), (MAN, _("male")), (WOMAN, _("female")), (OTHER, _("other")))

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
        (PENDING, _("in novice list")),
        (ON_HOLD, _("waiting for first ten entries")),
        (APPROVED, _("authorship approved")),
    )

    # Receiving messages options
    DISABLED = "DS"
    ALL_USERS = "AU"
    AUTHOR_ONLY = "AO"
    FOLLOWING_ONLY = "FO"
    MESSAGE_PREFERENCE = (
        (DISABLED, _("nobody")),
        (ALL_USERS, _("authors and novices")),
        (AUTHOR_ONLY, _("authors")),
        (FOLLOWING_ONLY, _("people who i follow")),
    )

    # Base auth related fields, notice: username field will be used for nicknames
    username = models.CharField(
        "nick",
        max_length=35,
        unique=True,
        help_text=_(
            "the nickname that will represent you in the site."
            " can be 3-35 characters long, can include only letters, numbers and spaces"
        ),
        validators=[
            validate_username_partial,
            AuthorNickValidator(),
            MinLengthValidator(3, _("this nickname is too tiny")),
        ],
        error_messages={"unique": _("this nickname is already taken")},
    )

    slug = models.SlugField(max_length=35, unique=True, editable=False)
    email = models.EmailField(_("e-mail"), unique=True)
    is_active = models.BooleanField(default=False, verbose_name=_("active"))

    # Base auth field settings
    USERNAME_FIELD = "email"

    # A list of the field names that will be prompted for when creating a user via the createsuperuser command.
    REQUIRED_FIELDS = ["username", "is_active"]

    # Novice application related fields
    is_novice = models.BooleanField(default=True, verbose_name=_("novice"))
    application_status = models.CharField(max_length=2, choices=APPLICATION_STATUS, default=ON_HOLD)
    application_date = models.DateTimeField(null=True, blank=True, default=None)
    last_activity = models.DateTimeField(null=True, blank=True, default=None)
    queue_priority = models.PositiveSmallIntegerField(default=0)

    # Accessibility details
    suspended_until = models.DateTimeField(null=True, blank=True, default=None)
    is_frozen = models.BooleanField(default=False, verbose_name=_("Frozen"))
    is_private = models.BooleanField(default=False, verbose_name=_("Anonymous"))

    # User-user relations
    following = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")
    blocked = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="blocked_by")

    # User-entry relations
    favorite_entries = models.ManyToManyField(
        "Entry", through="EntryFavorites", related_name="favorited_by", blank=True
    )

    upvoted_entries = models.ManyToManyField("Entry", through="UpvotedEntries", related_name="upvoted_by", blank=True)

    downvoted_entries = models.ManyToManyField(
        "Entry", through="DownvotedEntries", related_name="downvoted_by", blank=True
    )

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
    allow_receipts = models.BooleanField(default=True)

    # Other
    karma = models.DecimalField(default=Decimal(0), max_digits=7, decimal_places=2)
    badges = models.ManyToManyField("Badge", blank=True)

    announcement_read = models.DateTimeField(auto_now_add=True)

    # https://docs.djangoproject.com/en/3.0/topics/db/managers/#django.db.models.Model._default_manager
    objects = UserManager()
    objects_accessible = AuthorManagerAccessible()
    in_novice_list = InNoviceList()

    def __str__(self):
        return f"{self.username}:{self.id}"

    class Meta:
        permissions = (
            ("can_activate_user", _("Can access to the novice list")),
            ("suspend_user", _("Can suspend users")),
            ("can_clear_cache", _("Can clear cache")),
            ("can_comment", _("Can comment on entries")),
            ("can_suggest_categories", _("Can suggest categories for topics")),
        )
        verbose_name = _("author")
        verbose_name_plural = _("authors")

    def save(self, *args, **kwargs):
        created = self.pk is None  # If True, the user is created (not updated).

        if created:
            self.slug = uuslug(self.username, instance=self)

        super().save(*args, **kwargs)

        if created:
            self.following_categories.add(*Category.objects.filter(is_default=True))

    def get_absolute_url(self):
        return reverse("user-profile", kwargs={"slug": self.slug})

    def delete(self, *args, **kwargs):
        # Archive conversations of target users.
        for conversation in self.targeted_conversations.all():
            conversation.archive()

        return super().delete(*args, **kwargs)

    def get_following_topics_with_receipt(self):
        """Get user's following topics with read receipts."""
        return self.following_topics.annotate(
            count=(
                Count(
                    "entries",
                    filter=(
                        Q(entries__date_created__gte=F("topicfollowing__read_at"))
                        & ~(
                            Q(entries__author=self)
                            | Q(entries__author__in=self.blocked.all())
                            | Q(entries__author__is_novice=True)
                            | Q(entries__is_draft=True)
                        )
                    ),
                )
            ),
            last_read_at=F("topicfollowing__read_at"),
            is_read=Case(When(Q(count__gt=0), then=False), default=True, output_field=BooleanField()),
        )

    def get_entry_count_by_threshold(self, **timedelta_kwargs):
        return (
            self.entry_set(manager="objects_published")
            .filter(date_created__gte=time_threshold(**timedelta_kwargs))
            .count()
        )

    def has_exceeded_vote_limit(self, against=None):
        """Check vote limits. This is done before the vote is registered."""

        # Notice: couldn't filter on unions, so both models are explicitly written.
        h24 = {"date_created__gte": time_threshold(hours=24)}  # Filter objects that has been created in last 24 hours.

        upvoted = UpvotedEntries.objects.filter(author=self)
        downvoted = DownvotedEntries.objects.filter(author=self)

        daily_vote_count = upvoted.filter(**h24).count() + downvoted.filter(**h24).count()

        if daily_vote_count >= DAILY_VOTE_LIMIT:
            return True, gettext("you have used up all the vote claims you have today. try again later.")

        if against:
            upvoted_against = upvoted.filter(entry__author=against).count()
            downvoted_against = downvoted.filter(entry__author=against).count()
            total_votes_against = upvoted_against + downvoted_against

            if total_votes_against >= TOTAL_VOTE_LIMIT_PER_USER:
                return True, gettext("sorry, you have been haunting this person for a long time.")

            daily_upvoted_against = upvoted.filter(entry__author=against, **h24).count()
            daily_downvoted_against = downvoted.filter(entry__author=against, **h24).count()
            daily_votes_against = daily_upvoted_against + daily_downvoted_against

            if daily_votes_against >= DAILY_VOTE_LIMIT_PER_USER:
                return True, gettext("this person has taken enough of your votes today, maybe try other users?")

        return False, None

    def can_send_message(self, recipient=None):
        if self == recipient:
            return False

        if self == get_generic_superuser():
            return True

        if (
            (recipient.is_frozen or recipient.is_private or (not recipient.is_active))
            or (recipient.message_preference == Author.DISABLED)
            or (self.is_novice and recipient.message_preference == Author.AUTHOR_ONLY)
            or (
                recipient.message_preference == Author.FOLLOWING_ONLY
                and not recipient.following.filter(pk=self.pk).exists()
            )
            or (recipient.blocked.filter(pk=self.pk).exists() or self.blocked.filter(pk=recipient.pk).exists())
        ):
            return False

        return True

    @property
    def generation(self):
        if DISABLE_GENERATIONS:
            return None

        gen_start_date = parse_date_or_none(FIRST_GENERATION_DATE)

        if gen_start_date is None:
            raise ValueError("Invalid configuration for 'FIRST_GENERATION_DATE'. Please provide a valid date.")

        delta = self.date_joined - gen_start_date
        return math.ceil((delta.days / GENERATION_GAP_DAYS) or 1)

    @cached_property
    def karma_flair(self):
        karma = round(self.karma)

        if karma <= KARMA_BOUNDARY_LOWER:
            return f"{UNDERWHELMING_KARMA_EXPRESSION} ({karma})"

        if karma >= KARMA_BOUNDARY_UPPER:
            return f"{OVERWHELMING_KARMA_EXPRESSION} ({karma})"

        for key in KARMA_EXPRESSIONS:
            if karma in key:
                return f"{KARMA_EXPRESSIONS[key]} ({karma})"

        return None

    @property
    def is_karma_eligible(self):
        """Eligible users will be able to influence other users' karma points by voting."""
        return not (self.is_novice or self.is_suspended or self.karma <= KARMA_BOUNDARY_LOWER)

    @property
    def entry_count(self):
        return self.entry_set(manager="objects_published").count()

    @property
    def entry_count_month(self):
        return self.get_entry_count_by_threshold(days=30)

    @property
    def entry_count_week(self):
        return self.get_entry_count_by_threshold(days=7)

    @property
    def entry_count_day(self):
        return self.get_entry_count_by_threshold(days=1)

    @property
    def last_entry_date(self):
        with suppress(ObjectDoesNotExist):
            return self.entry_set(manager="objects_published").latest("date_created").date_created

        return None

    @property
    def followers(self):
        return Author.objects.filter(following=self)

    @property
    def entry_nice(self):
        return (
            self.entry_set(manager="objects_published")
            .filter(vote_rate__gt=Decimal("1"))
            .order_by("-vote_rate")
            .first()
        )

    @property
    def email_confirmed(self):
        return not self.userverification_set.filter(expiration_date__gte=time_threshold(hours=24)).exists()

    @property
    def is_suspended(self):
        return self.suspended_until is not None and self.suspended_until > timezone.now()

    @property
    def is_accessible(self):
        return not (self.is_frozen or (not self.is_active) or self.is_private or self.is_suspended)

    @cached_property
    def unread_message_count(self):
        return self.conversations.aggregate(
            count=Count("messages", filter=Q(messages__recipient=self, messages__read_at__isnull=True))
        )["count"]

    @cached_property
    def unread_topic_count(self):
        """Find counts for unread topics and announcements."""
        unread_announcements = (
            apps.get_model("dictionary.Announcement")
            .objects.filter(notify=True, date_created__lte=timezone.now(), date_created__gte=self.announcement_read)
            .count()
        )
        unread_topics = self.get_following_topics_with_receipt().aggregate(sum=Coalesce(Sum("count"), 0))["sum"]
        return {
            "sum": unread_announcements + unread_topics,
            "announcements": unread_announcements,
            "topics": unread_topics,
        }

    @cached_property
    def novice_queue(self):
        if self.last_activity < time_threshold(hours=24):
            # NoviceActivityMiddleware ensures that logged in novices will always
            # pass this check. It is not possible to see the queue of users
            # with no activity in last one day.
            return None

        def interqueue(user):
            active_siblings = Author.in_novice_list.annotate_activity(
                Author.in_novice_list.exclude(pk=user.pk).filter(queue_priority=user.queue_priority)
            ).filter(is_active_today=True)

            if active_siblings.exists():
                return active_siblings.filter(application_date__lt=user.application_date).count() + 1
            return 1

        equal_and_superior = Author.in_novice_list.exclude(pk=self.pk).filter(queue_priority__gte=self.queue_priority)

        if equal_and_superior.count():
            superior = equal_and_superior.filter(queue_priority__gt=self.queue_priority)

            if superior_count := superior.count():
                return superior_count + interqueue(self)
            return interqueue(self)
        return 1


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
    STATES = (
        (NO_TRACE, _("delete account completely")),
        (LEGACY, _("delete account with legacy")),
        (FROZEN, _("freeze account")),
    )

    author = models.OneToOneField(Author, on_delete=models.CASCADE)
    state = models.CharField(max_length=2, choices=STATES, default=FROZEN, verbose_name=_("last words?"))
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


class Badge(models.Model):
    name = models.CharField(max_length=36, verbose_name=_("Name"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    url = models.URLField(
        null=True,
        blank=True,
        verbose_name=_("Link"),
        help_text=_(
            "The link to follow when users click the badge. If no link is provided, related topic will be used."
        ),
    )

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = _("badge")
        verbose_name_plural = _("badges")
