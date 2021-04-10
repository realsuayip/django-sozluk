import math
import random

from contextlib import suppress
from decimal import Decimal
from functools import wraps

from django.apps import apps
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import BooleanField, Case, Count, F, OuterRef, Q, Sum, When
from django.db.models.functions import Coalesce
from django.shortcuts import reverse
from django.template import defaultfilters
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _, ngettext

from uuslug import uuslug

from dictionary.conf import settings
from dictionary.models.category import Category
from dictionary.models.entry import Entry
from dictionary.models.m2m import DownvotedEntries, UpvotedEntries
from dictionary.models.managers.author import AccountTerminationQueueManager, AuthorManagerAccessible, InNoviceList
from dictionary.utils import get_generic_superuser, parse_date_or_none, time_threshold
from dictionary.utils.db import SubQueryCount
from dictionary.utils.decorators import cached_context
from dictionary.utils.serializers import ArchiveSerializer
from dictionary.utils.validators import validate_username_partial


def usercache(initial_func=None, *, timeout=86400):
    """
    Caches model method, uses model instance in cache key.
    Basically a wrapper around cached_context.
    """

    def inner(method):
        @wraps(method)
        def wrapped(self, *args, **kwargs):
            return cached_context(prefix="usercache_" + method.__name__, vary_on_user=True, timeout=timeout)(
                lambda user=None: method(self, *args, **kwargs)
            )(user=self)

        return wrapped

    if initial_func:
        return inner(initial_func)

    return inner


class AuthorNickValidator(UnicodeUsernameValidator):
    regex = r"^[a-z0-9]+(\ [a-z0-9]+)*$"
    message = _("unlike what you sent, an appropriate nickname would only consist of letters, numbers and spaces.")


class Author(AbstractUser):
    class Gender(models.TextChoices):
        MAN = "MN", _("male")
        WOMAN = "WM", _("female")
        OTHER = "OT", _("other")
        UNKNOWN = "NO", _("forget it")

    class Status(models.TextChoices):
        PENDING = "PN", _("in novice list")
        ON_HOLD = "OH", _("waiting for first ten entries")
        APPROVED = "AP", _("authorship approved")

    class MessagePref(models.TextChoices):
        DISABLED = "DS", _("nobody")
        ALL_USERS = "AU", _("authors and novices")
        AUTHOR_ONLY = "AO", _("authors")
        FOLLOWING_ONLY = "FO", _("people who i follow")

    class Theme(models.TextChoices):
        LIGHT = "light", _("Light")
        DARK = "dark", _("Dark")

    class EntryCount(models.IntegerChoices):
        TEN = 10, "10"
        THIRTY = 30, "30"
        FIFTY = 50, "50"
        HUNDRED = 100, "100"

    class TopicCount(models.IntegerChoices):
        THIRTY = 30, "30"
        FIFTY = 50, "50"
        SEVENTY_FIVE = 75, "75"
        HUNDRED = 100, "100"

    # Base auth related fields, notice: username field will be used for nicknames
    username = models.CharField(
        _("nickname"),
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
    is_novice = models.BooleanField(db_index=True, default=True, verbose_name=_("Novice status"))
    application_status = models.CharField(
        max_length=2, choices=Status.choices, default=Status.ON_HOLD, verbose_name=_("Application status")
    )
    application_date = models.DateTimeField(null=True, blank=True, default=None, verbose_name=_("Application date"))
    last_activity = models.DateTimeField(null=True, blank=True, default=None, verbose_name=_("Last activity as novice"))
    queue_priority = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Queue priority"),
        help_text=_("Novices with high priority are more likely to appear on the top of the novice list."),
    )

    # Accessibility details
    suspended_until = models.DateTimeField(null=True, blank=True, default=None, verbose_name=_("Suspended until"))
    is_frozen = models.BooleanField(default=False, verbose_name=_("Frozen status"))
    is_private = models.BooleanField(default=False, verbose_name=_("Anonymous status"))

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
    allow_uncategorized = models.BooleanField(default=True)

    # User-topic relations
    following_topics = models.ManyToManyField("Topic", through="TopicFollowing", related_name="followers", blank=True)

    # Personal info
    birth_date = models.DateField(blank=True, null=True, verbose_name=_("Birth date"))
    gender = models.CharField(max_length=2, choices=Gender.choices, default=Gender.UNKNOWN, verbose_name=_("Gender"))

    # Preferences
    entries_per_page = models.IntegerField(choices=EntryCount.choices, default=EntryCount.TEN)
    topics_per_page = models.IntegerField(choices=TopicCount.choices, default=TopicCount.FIFTY)
    message_preference = models.CharField(max_length=2, choices=MessagePref.choices, default=MessagePref.ALL_USERS)
    pinned_entry = models.OneToOneField("Entry", blank=True, null=True, on_delete=models.SET_NULL, related_name="+")
    allow_receipts = models.BooleanField(default=True)
    allow_site_announcements = models.BooleanField(default=True)
    theme = models.CharField(choices=Theme.choices, default=Theme.LIGHT, max_length=10)

    # Other
    karma = models.DecimalField(default=Decimal(0), max_digits=7, decimal_places=2, verbose_name=_("Karma points"))
    badges = models.ManyToManyField("Badge", blank=True, verbose_name=_("Badges"))

    announcement_read = models.DateTimeField(auto_now_add=True)

    # https://docs.djangoproject.com/en/3.0/topics/db/managers/#django.db.models.Model._default_manager
    objects = UserManager()
    objects_accessible = AuthorManagerAccessible()
    in_novice_list = InNoviceList()

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

    def __str__(self):
        return str(self.username)

    def save(self, *args, **kwargs):
        created = self.pk is None  # If True, the user is created (not updated).

        if created:
            self.slug = uuslug(self.username, instance=self)

        super().save(*args, **kwargs)

        if created:
            self.following_categories.add(*Category.objects.filter(is_default=True))

    def delete(self, *args, **kwargs):
        # Archive conversations of target users.
        targeted_conversations = self.targeted_conversations.select_related("holder", "target").prefetch_related(
            "messages"
        )

        for conversation in targeted_conversations:
            conversation.archive()

        return super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("user-profile", kwargs={"slug": self.slug})

    def get_following_topics_with_receipt(self):
        """Get user's following topics with read receipts."""
        new_entries = (
            Entry.objects.filter(topic=OuterRef("pk"), date_created__gte=OuterRef("topicfollowing__read_at"))
            .exclude(Q(author=self) | Q(author__in=self.blocked.all()))
            .only("id")
        )

        return self.following_topics.annotate(
            count=SubQueryCount(new_entries),
            last_read_at=F("topicfollowing__read_at"),
            is_read=Case(When(Q(count__gt=0), then=False), default=True, output_field=BooleanField()),
        )

    def get_entry_count_by_threshold(self, **timedelta_kwargs):
        return (
            self.entry_set(manager="objects_published")
            .filter(date_created__gte=time_threshold(**timedelta_kwargs))
            .count()
        )

    @usercache
    def get_best_entries(self):
        return tuple(self.entry_set(manager="objects_published").filter(vote_rate__gt=0).order_by("-vote_rate")[:50])

    def has_exceeded_vote_limit(self, against=None):
        """Check vote limits. This is done before the vote is registered."""

        # Notice: couldn't filter on unions, so both models are explicitly written.
        h24 = {"date_created__gte": time_threshold(hours=24)}  # Filter objects that has been created in last 24 hours.

        upvoted = UpvotedEntries.objects.filter(author=self)
        downvoted = DownvotedEntries.objects.filter(author=self)

        daily_vote_count = upvoted.filter(**h24).count() + downvoted.filter(**h24).count()

        if daily_vote_count >= settings.DAILY_VOTE_LIMIT:
            return True, gettext("you have used up all the vote claims you have today. try again later.")

        if against:
            upvoted_against = upvoted.filter(entry__author=against).count()
            downvoted_against = downvoted.filter(entry__author=against).count()
            total_votes_against = upvoted_against + downvoted_against

            if total_votes_against >= settings.TOTAL_VOTE_LIMIT_PER_USER:
                return True, gettext("sorry, you have been haunting this person for a long time.")

            daily_upvoted_against = upvoted.filter(entry__author=against, **h24).count()
            daily_downvoted_against = downvoted.filter(entry__author=against, **h24).count()
            daily_votes_against = daily_upvoted_against + daily_downvoted_against

            if daily_votes_against >= settings.DAILY_VOTE_LIMIT_PER_USER:
                return True, gettext("this person has taken enough of your votes today, maybe try other users?")

        return False, None

    def can_send_message(self, recipient=None):
        if self == recipient:
            return False

        if self.username == settings.GENERIC_SUPERUSER_USERNAME:
            return True

        if (
            (recipient.is_frozen or recipient.is_private or (not recipient.is_active))
            or (recipient.message_preference == Author.MessagePref.DISABLED)
            or (self.is_novice and recipient.message_preference == Author.MessagePref.AUTHOR_ONLY)
            or (
                recipient.message_preference == Author.MessagePref.FOLLOWING_ONLY
                and not recipient.following.filter(pk=self.pk).exists()
            )
            or (recipient.blocked.filter(pk=self.pk).exists() or self.blocked.filter(pk=recipient.pk).exists())
        ):
            return False

        return True

    @property
    def entry_publishable_status(self):
        """:return None if can publish new entries, else return apt error message."""

        if not self.is_accessible:
            return gettext("you lack the required permissions.")

        latest_entry_date = self.last_entry_date

        if latest_entry_date is None:
            return None

        interval = settings.NOVICE_ENTRY_INTERVAL if self.is_novice else settings.AUTHOR_ENTRY_INTERVAL
        delta = timezone.now() - latest_entry_date

        if delta <= timezone.timedelta(seconds=interval):
            remaining = interval - delta.seconds
            return (
                ngettext(
                    "you are sending entries too frequently. try again in a second.",
                    "you are sending entries too frequently. try again in %(remaining)d seconds.",
                    remaining,
                )
                % {"remaining": remaining}
            )

        return None

    @property
    def generation(self):
        if settings.DISABLE_GENERATIONS:
            return None

        gen_start_date = parse_date_or_none(settings.FIRST_GENERATION_DATE)

        if gen_start_date is None:
            raise ValueError("Invalid configuration for 'FIRST_GENERATION_DATE'. Please provide a valid date.")

        delta = self.date_joined - gen_start_date
        return math.ceil((delta.days / settings.GENERATION_GAP_DAYS) or 1)

    @cached_property
    def karma_flair(self):
        karma = round(self.karma)

        if karma <= settings.KARMA_BOUNDARY_LOWER:
            return f"{settings.UNDERWHELMING_KARMA_EXPRESSION} ({karma})"

        if karma >= settings.KARMA_BOUNDARY_UPPER:
            return f"{settings.OVERWHELMING_KARMA_EXPRESSION} ({karma})"

        for key in settings.KARMA_EXPRESSIONS:
            if karma in key:
                return f"{settings.KARMA_EXPRESSIONS[key]} ({karma})"

        return None

    @property
    def is_karma_eligible(self):
        """Eligible users will be able to influence other users' karma points by voting."""
        return not (self.is_novice or self.is_suspended or self.karma <= settings.KARMA_BOUNDARY_LOWER)

    @cached_property
    @usercache
    def entry_count(self):
        return self.entry_set(manager="objects_published").count()

    @cached_property
    @usercache
    def entry_count_month(self):
        return self.get_entry_count_by_threshold(days=30)

    @cached_property
    @usercache
    def entry_count_week(self):
        return self.get_entry_count_by_threshold(days=7)

    @cached_property
    @usercache
    def entry_count_day(self):
        return self.get_entry_count_by_threshold(days=1)

    @cached_property
    @usercache
    def last_entry_date(self):
        with suppress(ObjectDoesNotExist):
            return self.entry_set(manager="objects_published").latest("date_created").date_created

        return None

    def invalidate_entry_counts(self):
        names = ("entry_count", "entry_count_month", "entry_count_week", "entry_count_day", "last_entry_date")
        for name in names:
            key = f"usercache_{name}_context__<lambda>_usr{self.pk}"
            cache.delete(key)

    @property
    def followers(self):
        return Author.objects.filter(following=self)

    @cached_property
    def entry_nice(self):
        """A random entry selected from the best entries of the user."""
        best_entries = self.get_best_entries()

        if not best_entries:
            return None

        return random.choice(best_entries)

    @property
    def email_confirmed(self):
        return not self.userverification_set.filter(expiration_date__gte=time_threshold(hours=24)).exists()

    @property
    def is_suspended(self):
        return self.suspended_until is not None and self.suspended_until > timezone.now()

    @property
    def is_accessible(self):
        return not (self.is_hidden or self.is_suspended)

    @property
    def is_hidden(self):
        return self.is_frozen or (not self.is_active) or self.is_private

    @cached_property
    def unread_message_count(self):
        return self.conversations.aggregate(
            count=Count("messages", filter=Q(messages__recipient=self, messages__read_at__isnull=True))
        )["count"]

    @cached_property
    @usercache(timeout=60)
    def unread_topic_count(self):
        """
        Find counts for unread topics and announcements (displayed in header when apt).

        This query seems to be too expensive to be called in every request. So it is called
        every <timeout> seconds. In following topic list, the cache gets invalidated each
        request, making that page fresh every time. Actions which might change this data
        also invalidates this cache. e.g. reading an unread topic/announcement.
        """

        unread_announcements = (
            (
                apps.get_model("dictionary.Announcement")
                .objects.filter(notify=True, date_created__lte=timezone.now(), date_created__gte=self.announcement_read)
                .count()
            )
            if self.allow_site_announcements
            else 0
        )
        unread_topics = self.get_following_topics_with_receipt().aggregate(sum=Coalesce(Sum("count"), 0))["sum"]
        return {
            "sum": unread_announcements + unread_topics,
            "announcements": unread_announcements,
            "topics": unread_topics,
        }

    def invalidate_unread_topic_count(self):
        """Invalidates cache of unread_topic_count, set by cached_context."""
        return cache.delete(f"usercache_unread_topic_count_context__<lambda>_usr{self.pk}")

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

        if equal_and_superior.exists():
            superior = equal_and_superior.filter(queue_priority__gt=self.queue_priority)

            if superior_count := superior.count():
                return superior_count + interqueue(self)
            return interqueue(self)
        return 1


class Memento(models.Model):
    body = models.TextField(blank=True)
    holder = models.ForeignKey(Author, on_delete=models.CASCADE)
    patient = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="+")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["holder", "patient"], name="unique_memento")]

    def __str__(self):
        return f"{self.__class__.__name__}#{self.id}, from {self.holder} about {self.patient}"


class UserVerification(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    verification_token = models.CharField(max_length=128)
    new_email = models.EmailField(blank=True)  # new e-mail if it is subject to change
    expiration_date = models.DateTimeField()

    def save(self, *args, **kwargs):
        UserVerification.objects.filter(author=self.author).delete()
        super().save(*args, **kwargs)


class AccountTerminationQueue(models.Model):
    class State(models.TextChoices):
        NO_TRACE = "NT", _("delete account completely")
        LEGACY = "LE", _("delete account with legacy")
        FROZEN = "FZ", _("freeze account")

    author = models.OneToOneField(Author, on_delete=models.CASCADE)
    state = models.CharField(max_length=2, choices=State.choices, default=State.FROZEN, verbose_name=_("last words?"))
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

            if self.state != self.State.FROZEN:
                self.termination_date = timezone.now() + timezone.timedelta(hours=120)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.author.is_frozen = False
        self.author.save()
        super().delete(*args, **kwargs)


class Badge(models.Model):
    name = models.CharField(max_length=36, verbose_name=_("Name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    url = models.URLField(
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


def user_directory_backup(instance, _filename):
    date_str = defaultfilters.date(timezone.localtime(timezone.now()), "Y-m-d")
    return f"backup/{instance.author.pk}/backup-{date_str}.json"


class BackUp(models.Model):
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_directory_backup)
    is_ready = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def process(self):
        if self.is_ready:
            return

        serializer = ArchiveSerializer()
        entries = self.author.entry_set(manager="objects_published").select_related("topic")
        conversations = self.author.conversationarchive_set.all()

        entries_text = serializer.serialize(entries, fields=("topic__title", "content", "date_created", "date_edited"))
        conversations_text = (
            "[%s]"
            % "".join('{"target": "%s", "messages": %s},' % (item.target, item.messages) for item in conversations)[:-1]
        )  # Formatting already-serialized data ([:-1] removes the trailing comma).

        content = '{"entries": %s, "conversations": %s}' % (entries_text, conversations_text)
        self.is_ready = True
        self.file.save("backup", ContentFile(content.encode("utf-8")), save=True)

        settings.get_model("Message").objects.compose(
            get_generic_superuser(),
            self.author,
            gettext(
                "your backup is now ready. you may download your backup"
                " file using the link provided in the backup tab of settings."
            ),
        )

    def process_async(self):
        from dictionary.tasks import process_backup  # noqa

        process_backup.delay(self.pk)

    def delete(self, **kwargs):
        super().delete(**kwargs)
        self.file.delete(save=False)
