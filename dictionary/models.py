from django.db import models
from django.contrib.auth.models import User, AbstractUser
from uuslug import uuslug
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count, Max, F, Q
from decimal import Decimal
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils import timezone
import datetime


# todo modal mesaj temizleme
# NOT: table wide == MANAGER, row wide = MODAL METHOD


class AuthorNickValidator(UnicodeUsernameValidator):
    regex = r'^[a-z\ ]+$'
    message = _("boşluk dışında türkçe ve özel karakter içermeyen alfabe harflerinden oluşan bir nick münasiptir")


class Author(AbstractUser):
    # Any changes made in models.py regarding choicefields should also be made in forms.py
    # genders
    MAN = 'MN'
    WOMAN = 'WM'
    OTHER = 'OT'
    UNKNOWN = 'NO'
    GENDERS = ((MAN, 'erkek'), (WOMAN, 'kadın'), (OTHER, 'diğer'), (UNKNOWN, 'boşver'))

    # entry per page preference
    TEN = 10
    THIRTY = 30
    FIFTY = 50
    ONEHUNDRED = 100
    ENTRY_COUNTS = ((TEN, "10"), (THIRTY, "30"), (FIFTY, "50"), (ONEHUNDRED, "100"))

    # status of author queue
    PENDING = "PN"
    ON_HOLD = "OH"
    APPROVED = "AP"
    APPLICATION_STATUS = (
        (PENDING, "çaylak listesinde"), (ON_HOLD, "entry girmesi bekleniyor"), (APPROVED, "yazar oldu"))

    #  recieving messages preference
    DISABLED = "DS"
    ALL_USERS = "AU"
    AUTHOR_ONLY = "AO"
    FOLLOWING_ONLY = "FO"
    MESSAGE_PREFERENCE = ((DISABLED, "hiçkimse"), (ALL_USERS, "yazar ve çaylaklar"), (AUTHOR_ONLY, "yazarlar"),
                          (FOLLOWING_ONLY, "takip ettiklerim"))

    nick_validator = AuthorNickValidator()
    username = models.CharField(_('username'), max_length=50, unique=True, help_text=_(
        'şart. en fazla 50 karakter uzunluğunda, boşluk içerebilir özel ve türkçe karakter içeremez'),
                                validators=[nick_validator], error_messages={'unique': _("bu nick kapılmış"), }, )

    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=2, choices=GENDERS, default=UNKNOWN)
    is_novice = models.BooleanField(default=True)
    application_status = models.CharField(max_length=2, choices=APPLICATION_STATUS, default=ON_HOLD)
    application_date = models.DateTimeField(null=True, blank=True, default=None)
    last_activity = models.DateTimeField(null=True, blank=True, default=None)  # NOT NULL
    banned_until = models.DateTimeField(null=True, blank=True, default=None)
    following = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")
    blocked = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="+")
    entries_per_page = models.IntegerField(choices=ENTRY_COUNTS, default=TEN)
    message_preference = models.CharField(max_length=2, choices=MESSAGE_PREFERENCE, default=ALL_USERS)
    favorite_entries = models.ManyToManyField('Entry', related_name="favorited_by", blank=True)
    upvoted_entries = models.ManyToManyField('Entry', related_name="upvoted_by", blank=True)
    downvoted_entries = models.ManyToManyField('Entry', related_name="downvoted_by", blank=True)
    pinned_entry = models.OneToOneField('Entry', blank=True, null=True, on_delete=models.SET_NULL, related_name="+")
    email = models.EmailField(_('email adresi'), unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # notice: username field will be used for nicknames

    class Meta:
        # Superusers need to have this permission to accept a novice as an author.
        permissions = (("can_activate_user", "Make author"),)

    @property
    def entry_count(self):
        return Entry.objects_published.filter(author=self).count()

    @property
    def entry_count_month(self):
        return Entry.objects_published.filter(author=self,
                                              date_created__gte=timezone.now() - datetime.timedelta(days=30)).count()

    @property
    def entry_count_week(self):
        return Entry.objects_published.filter(author=self,
                                              date_created__gte=timezone.now() - datetime.timedelta(days=7)).count()

    @property
    def entry_count_day(self):
        return Entry.objects_published.filter(author=self,
                                              date_created__gte=timezone.now() - datetime.timedelta(days=1)).count()

    @property
    def last_entry_date(self):
        return Entry.objects_published.filter(author=self).latest("date_created").date_created

    @property
    def entries(self):
        return Entry.objects_published.filter(author=self)

    @property
    def followers(self):
        return Author.objects.filter(following=self)

    @property
    def entry_nice(self):
        entry = Entry.objects_published.filter(author=self).order_by("-vote_rate").first()
        if entry and entry.vote_rate > Decimal("1"):
            return entry
        else:
            return None

    def __str__(self):
        return f"{self.username}:{self.id}"


class Category(models.Model):
    name = models.CharField(max_length=24, unique=True)
    slug = models.SlugField(max_length=64, unique=False, blank=True)
    description = models.TextField()
    weight = models.SmallIntegerField(default=0)

    class Meta:
        ordering = ["-weight"]

    def save(self, *args, **kwargs):
        self.slug = uuslug(self.name, instance=self)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"


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


class EntryManager(models.Manager):
    # Includes ONLY the PUBLISHED entries by NON-NOVICE authors
    def get_queryset(self):
        # also for çaylar todo
        return super().get_queryset().exclude(Q(is_draft=True) | Q(author__is_novice=True))


class EntryManagerAll(models.Manager):
    # Includes ALL entries (entries by novices, drafts)
    pass


class EntryManagerOnlyNovices(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(author__is_novice=False)


class EntryManagerOnlyPublished(models.Manager):
    # Includes ONLY the PUBLISHED entries (entries by NOVICE users still visible)
    def get_queryset(self):
        return super().get_queryset().exclude(is_draft=True)


class Entry(models.Model):
    topic = models.ForeignKey(Topic,
                              on_delete=models.PROTECT)  # don't use topic_set because there are many managers for Entry
    author = models.ForeignKey(Author, on_delete=models.PROTECT)
    content = models.TextField()
    date_created = models.DateTimeField(auto_now_add=True)
    date_edited = models.DateTimeField(blank=True, null=True, default=None)  # edit feature gelince otomatik set et todo
    vote_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal(0))
    is_draft = models.BooleanField(default=False)

    # notice: all these managers are created after the usages, so there may be some leftovers which need to be corrected
    # manager to work properly. reviese todo
    objects_all = EntryManagerAll()
    objects_published = EntryManagerOnlyPublished()
    objects_novices = EntryManagerOnlyNovices()
    objects = EntryManager()

    class Meta:
        ordering = ["date_created"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.author.is_novice and self.author.application_status == "OH":
            # Check if the user has written 10 entries, If so make them available for novice lookup
            if self.author.entry_count >= 10:
                self.author.application_status = "PN"
                self.author.application_date = timezone.now()
                self.author.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        if self.author.is_novice and self.author.application_status == "PN":
            # if the entry count drops less than 10, remove user from novice lookup
            # does not work if bulk deletion made on admin panel (users can only remove one entry at a time)
            # todo not tested
            if self.author.entry_count < 10:
                self.author.application_status = "OH"
                self.author.application_date = None
                self.author.save()

    def __str__(self):
        return f"{self.id}#{self.author}"

    def update_vote(self, rate, change=False):
        a = Decimal("2") if change else Decimal("1")
        self.vote_rate = F("vote_rate") + rate * a
        self.save()


class MessageManager(models.Manager):
    def compose(self, sender, recipient, body):
        if sender == recipient or sender in recipient.blocked.all() or recipient in sender.blocked.all():
            return False

        message = self.create(sender=sender, recipient=recipient, body=body)
        return message


class Message(models.Model):
    body = models.TextField()
    sender = models.ForeignKey(Author, related_name="+", on_delete=models.PROTECT)
    recipient = models.ForeignKey(Author, related_name="+", on_delete=models.PROTECT)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    objects = MessageManager()

    def __str__(self):
        return f"{self.pk}"


class ConversationManager(models.Manager):
    def list_for_user(self, user):
        # todo yanlış query, !!
        # bu query düz mantıkla yazılmalı part.._in = user, order by messages snet at.
        return self.filter(participants__in=[user]).annotate(message_sent_last=Max('messages__sent_at')).order_by(
            "-message_sent_last")

    def with_user(self, sender, recipient):
        users = [sender, recipient]
        conversation = self.annotate(count=Count('participants')).filter(count=2)
        for user in users:
            conversation = conversation.filter(participants__pk=user.pk)
        return conversation.first()


class Conversation(models.Model):
    participants = models.ManyToManyField(Author)
    messages = models.ManyToManyField(Message)

    objects = ConversationManager()

    def __str__(self):
        return f"{self.id}{self.participants.values_list('username', flat=True)}"

    @property
    def last_message(self):
        return self.messages.latest(field_name="sent_at")


class Memento(models.Model):
    body = models.TextField()
    holder = models.ForeignKey(Author, on_delete=models.CASCADE)
    patient = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="+")

    def __str__(self):
        return f"{self.__class__.__name__}#{self.id}, from {self.holder} about {self.patient}"


@receiver(post_save, sender=Message, dispatch_uid="create_conversation")
def create_conversation(sender, instance, **kwargs):
    """
        1) Creates a conversation if user messages the other for the first time
        2) Adds messages to conversation
    """
    users = [instance.sender, instance.recipient]
    # Find conversation object for these 2 users
    conversation = Conversation.objects.annotate(count=Count('participants')).filter(count=2)
    for user in users:
        conversation = conversation.filter(participants__pk=user.pk)

    if not conversation.exists():
        conversation = Conversation.objects.create()
        conversation.participants.set([instance.sender, instance.recipient])
        conversation.messages.add(instance)
    else:
        conversation.first().messages.add(instance)
