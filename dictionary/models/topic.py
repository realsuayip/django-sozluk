from django.db import models
from django.shortcuts import reverse
from django.utils.translation import gettext, gettext_lazy as _

from uuslug import uuslug

from dictionary.models.author import Author
from dictionary.models.category import Category
from dictionary.models.m2m import TopicFollowing
from dictionary.models.managers.topic import TopicManager, TopicManagerPublished
from dictionary.models.messaging import Message
from dictionary.utils import get_generic_superuser, i18n_lower
from dictionary.utils.validators import validate_topic_title, validate_user_text


class Topic(models.Model):
    title = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        validators=[validate_topic_title],
        verbose_name=_("Definition"),
        help_text=_(
            "In order to change the definition of the topic after it"
            " has been created, you need to use topic moving feature."
        ),
    )

    slug = models.SlugField(max_length=96, unique=True, editable=False)

    created_by = models.ForeignKey(
        Author,
        null=True,
        editable=False,
        on_delete=models.SET_NULL,
        verbose_name=_("First user to write an entry"),
        help_text=_("The author or novice who entered the first entry for this topic publicly."),
    )

    category = models.ManyToManyField(Category, blank=True, verbose_name=_("Channels"))

    allow_suggestions = models.BooleanField(
        default=True,
        verbose_name=_("Allow suggestions"),
        help_text=_("When checked, users will be able to suggest channels to this topic."),
    )

    mirrors = models.ManyToManyField(
        "self",
        blank=True,
        verbose_name=_("Title disambiguation"),
        help_text=_(
            "<p style='color: #ba2121'><b>Warning!</b> The topics that you enter will automatically"
            " get related disambiguations. For this reason you should be working on a main topic that you"
            " selected.<br> Removing a topic from will cause the removal of <b>ALL</b> disambiguations, so"
            " you should note down the topics that you don't want to be removed to add them later.</p>"
        ),
    )

    media = models.TextField(blank=True, verbose_name=_("Media links"))

    is_banned = models.BooleanField(
        default=False,
        verbose_name=_("Prohibited"),
        help_text=_("Check this if you want to hinder authors and novices from entering new entries to this topic."),
    )

    is_censored = models.BooleanField(
        default=False,
        verbose_name=_("Censored"),
        help_text=_(
            "Check this if you don't want this topic to appear"
            " in in-site searches and <strong>public</strong> topic lists."
        ),
    )

    is_pinned = models.BooleanField(
        default=False,
        verbose_name=_("Pinned"),
        help_text=_(
            "Check this if you want this topic to be pinned in popular topics."
            "<br>The topic needs to have at least one entry."
        ),
    )

    is_ama = models.BooleanField(
        default=False,
        verbose_name=_("Ask me anything"),
        help_text=_(
            "If checked, comments will be visible in this topic. Authorized users will be able to comment on entries."
        ),
    )

    date_created = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date created"),
        help_text=_("<i>Might not always correspond to first entry.</i>"),
    )

    objects = TopicManager()
    objects_published = TopicManagerPublished()

    class Meta:
        permissions = (("move_topic", _("Can move topics")),)
        verbose_name = _("topic")
        verbose_name_plural = _("topics")

    def __str__(self):
        return str(self.title)

    def save(self, *args, **kwargs):
        self.title = i18n_lower(self.title)
        self.slug = uuslug(self.title, instance=self)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("topic", kwargs={"slug": self.slug})

    def follow_check(self, user):
        return TopicFollowing.objects.filter(topic=self, author=user).exists()

    def register_wishes(self, fulfiller_entry=None):
        """To delete fulfilled wishes and inform wishers."""

        if not (self.wishes.exists() and self.has_entries):
            return None

        invoked_by_entry = fulfiller_entry is not None
        wishes = self.wishes.all().select_related("author")

        for wish in wishes:
            self_fulfillment = invoked_by_entry and fulfiller_entry.author == wish.author

            if self_fulfillment:
                continue

            message = (
                gettext(
                    "`%(title)s`, the topic you wished for, had an entry"
                    " entered by `@%(username)s`: (see: #%(entry)d)"
                )
                % {
                    "title": self.title,
                    "username": fulfiller_entry.author.username,
                    "entry": fulfiller_entry.pk,
                }
                if invoked_by_entry
                else gettext("`%(title)s`, the topic you wished for, is now populated with some entries.")
                % {"title": self.title}
            )

            Message.objects.compose(get_generic_superuser(), wish.author, message)

        return wishes.delete()

    def wish_collection(self):
        return self.wishes.select_related("author")

    @property
    def exists(self):
        return True

    @property
    def valid(self):
        return True

    @property
    def entry_count(self):
        return self.entries(manager="objects_published").count()

    @property
    def has_entries(self):
        return self.entries.exclude(is_draft=True).exists()


class Wish(models.Model):
    author = models.ForeignKey("Author", on_delete=models.CASCADE, related_name="wishes", verbose_name=_("Author"))
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="wishes", verbose_name=_("Topic"))

    hint = models.TextField(validators=[validate_user_text], blank=True, verbose_name=_("Hint"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))

    class Meta:
        verbose_name = _("wish")
        verbose_name_plural = _("wishes")
        ordering = ("-date_created",)

    def __str__(self):
        return f"{self._meta.verbose_name.title()} #{self.pk} ({self.author.username})"
