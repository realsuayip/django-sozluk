import datetime
import time

from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.db import IntegrityError
from django.shortcuts import reverse
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from dictionary.conf import settings
from dictionary.models import (
    Author,
    Category,
    Conversation,
    Entry,
    GeneralReport,
    Memento,
    Message,
    Topic,
    TopicFollowing,
    UserVerification,
)


class AuthorModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.generic_superuser = Author.objects.create(
            username=settings.GENERIC_SUPERUSER_USERNAME, email="gsu", is_active=True
        )
        cls.author = Author.objects.create(username="user", email="0", is_active=True, is_novice=False)
        cls.topic = Topic.objects.create_topic("test_topic")
        cls.entry_base = {"topic": cls.topic, "author": cls.author}

    def test_profile_entry_counts(self):
        Entry.objects.create(**self.entry_base)  # created now (today)
        # dates to be mocked for auto now add field 'date_created'
        mock_31 = timezone.now() - datetime.timedelta(minutes=43201)  # month upper limit
        mock_30 = timezone.now() - datetime.timedelta(minutes=43199)  # created in 1 month period
        mock_14 = timezone.now() - datetime.timedelta(minutes=20159)  # created in 2 weeks period
        mock_8 = timezone.now() - datetime.timedelta(minutes=10081)  # week upper limit
        mock_7 = timezone.now() - datetime.timedelta(minutes=10079)  # created in 1 week period
        mock_2 = timezone.now() - datetime.timedelta(minutes=1441)  # today upper limit
        mock_1 = timezone.now() - datetime.timedelta(minutes=1439)  # created today

        mock_these = (mock_1, mock_2, mock_7, mock_8, mock_14, mock_30, mock_31)

        with mock.patch("django.utils.timezone.now") as mock_now:
            for retval in mock_these:
                mock_now.return_value = retval
                Entry.objects.create(**self.entry_base)

        self.assertEqual(self.author.entry_count, 8)
        self.assertEqual(self.author.entry_count_day, 2)
        self.assertEqual(self.author.entry_count_month, 7)
        self.assertEqual(self.author.entry_count_week, 4)

    def test_last_entry_date(self):
        Entry.objects.create(**self.entry_base, is_draft=True)
        self.assertIsNone(self.author.last_entry_date)

        del self.author.last_entry_date

        entry = Entry.objects.create(**self.entry_base)
        self.assertEqual(self.author.last_entry_date, entry.date_created)

    def test_followers(self):
        self.assertEqual(self.author.followers.count(), 0)  # no follower supplied yet
        follower = Author.objects.create(username="1", email="1")
        some_other_follower = Author.objects.create(username="2", email="2")
        follower.following.add(self.author)
        some_other_follower.following.add(self.author)
        self.assertIn(follower, self.author.followers)
        self.assertEqual(self.author.followers.count(), 2)

    def test_novice_list_join_retreat(self):
        """
        10 published entries needed in order an user to be in the novice list,
        if the number of entries drop to < 10
        user is removed from novice list

        del novice.entry_count -> Normally we don't expect multiple entry creation
        in one request; we need to delete cached_property to simulate that.
        """

        novice = Author.objects.create(username="noviceuser", email="noviceuser", is_active=True, is_novice=True)
        entry_base = {"topic": self.topic, "author": novice, "content": "123"}

        # Initial status
        self.assertEqual(novice.application_status, Author.Status.ON_HOLD)
        self.assertIsNone(novice.application_date)

        # Add NINE entries
        for _ in range(9):
            Entry.objects.create(**entry_base)
            del novice.entry_count

        # Add an entry which is a draft
        Entry.objects.create(**entry_base, is_draft=True)
        del novice.entry_count

        # There are 10 PUBLISHED entries required, 9 present, so everything should be the same
        self.assertEqual(novice.application_status, Author.Status.ON_HOLD)
        self.assertIsNone(novice.application_date)

        # Add 10th entry (user joins the novice list)
        final_entry = Entry.objects.create(**entry_base)
        del novice.entry_count

        self.assertEqual(novice.application_status, Author.Status.PENDING)
        self.assertIsNotNone(novice.application_date)

        final_entry.delete()  # delete 10th entry to retreat from novice list

        self.assertEqual(novice.application_status, Author.Status.ON_HOLD)
        self.assertIsNone(novice.application_date)

    def test_message_preferences(self):
        some_author = Author.objects.create(username="author", email="3", is_novice=False, is_active=True)
        some_novice = Author.objects.create(username="novice", email="4", is_active=True)
        frozen_account = Author.objects.create(username="frozen", email="5", is_frozen=True, is_active=True)
        private_account = Author.objects.create(username="private", email="6", is_private=True, is_active=True)
        inactive_account = Author.objects.create(username="inactive", email="7")

        # ALL users (database default)
        can_msg_sent_by_novice_public = Message.objects.compose(some_novice, self.author, "test")
        can_msg_sent_by_author_public = Message.objects.compose(some_author, self.author, "test")
        self.assertNotEqual(can_msg_sent_by_author_public, False)
        self.assertNotEqual(can_msg_sent_by_novice_public, False)

        # Disabled
        self.author.message_preference = Author.MessagePref.DISABLED
        can_msg_sent_by_novice_disabled = Message.objects.compose(some_novice, self.author, "test-")
        can_msg_sent_by_author_disabled = Message.objects.compose(some_author, self.author, "test-")
        can_msg_sent_by_gsuper_disabled = Message.objects.compose(self.generic_superuser, self.author, "test")
        self.assertEqual(can_msg_sent_by_author_disabled, False)
        self.assertEqual(can_msg_sent_by_novice_disabled, False)
        self.assertNotEqual(can_msg_sent_by_gsuper_disabled, False)

        # Authors (non-novices) only
        self.author.message_preference = Author.MessagePref.AUTHOR_ONLY
        msg_sent_by_novice = Message.objects.compose(some_novice, self.author, "test")
        msg_sent_by_author = Message.objects.compose(some_author, self.author, "test")
        msg_sent_by_gsuper = Message.objects.compose(self.generic_superuser, self.author, "test")
        self.assertNotEqual(msg_sent_by_author, False)
        self.assertEqual(msg_sent_by_novice, False)
        self.assertNotEqual(msg_sent_by_gsuper, False)

        # Following only
        self.author.message_preference = Author.MessagePref.FOLLOWING_ONLY
        msg_sent_by_non_follower = Message.objects.compose(some_author, self.author, "test")
        msg_sent_by_gsuper = Message.objects.compose(self.generic_superuser, self.author, "test")
        self.assertEqual(msg_sent_by_non_follower, False)
        self.assertNotEqual(msg_sent_by_gsuper, False)
        self.author.following.add(some_author)  # add following to send message
        msg_sent_by_follower = Message.objects.compose(some_author, self.author, "test")
        self.assertNotEqual(msg_sent_by_follower, False)

        # Blocking tests
        self.author.message_preference = Author.MessagePref.ALL_USERS
        self.author.blocked.add(some_author)
        can_recieve_msg_from_blocked_user = Message.objects.compose(some_author, self.author, "test")
        self.assertEqual(can_recieve_msg_from_blocked_user, False)
        can_send_msg_to_blocked_user = Message.objects.compose(self.author, some_author, "test")
        self.assertEqual(can_send_msg_to_blocked_user, False)

        self.author.blocked.add(self.generic_superuser)
        can_recieve_msg_from_blocked_gsuper = Message.objects.compose(self.generic_superuser, self.author, "test")
        self.assertNotEqual(can_recieve_msg_from_blocked_gsuper, False)

        # No self-messaging allowed
        can_send_message_to_self = Message.objects.compose(self.author, self.author, "test")
        self.assertEqual(can_send_message_to_self, False)

        # Frozen and private accounts can't be messaged
        can_send_message_to_frozen = Message.objects.compose(self.author, frozen_account, "test")
        can_send_message_to_private = Message.objects.compose(self.author, private_account, "test")
        can_send_message_to_frozen_gsuper = Message.objects.compose(self.generic_superuser, frozen_account, "test")
        can_send_message_to_private_gsuper = Message.objects.compose(self.generic_superuser, private_account, "test")
        self.assertEqual(can_send_message_to_frozen, False)
        self.assertEqual(can_send_message_to_private, False)
        self.assertNotEqual(can_send_message_to_frozen_gsuper, False)
        self.assertNotEqual(can_send_message_to_private_gsuper, False)

        # Inactive accounts can't be messaged
        can_send_message_to_inactive = Message.objects.compose(self.author, inactive_account, "test")
        can_send_message_to_inactive_gsuper = Message.objects.compose(self.generic_superuser, inactive_account, "test")
        self.assertEqual(can_send_message_to_inactive, False)
        self.assertNotEqual(can_send_message_to_inactive_gsuper, False)

    def test_follow_all_categories_on_creation(self):
        category_1 = Category.objects.create(name="test")
        Category.objects.create(name="test2")
        some_user = Author.objects.create(username="some_user", email="5")
        self.assertIn(category_1, some_user.following_categories.all())
        self.assertEqual(some_user.following_categories.all().count(), 2)

    def test_absolute_url(self):
        absolute_url = reverse("user-profile", kwargs={"slug": self.author.slug})
        self.assertEqual(absolute_url, self.author.get_absolute_url())

    def test_entry_nice(self):
        # No entry = No nice entry
        self.assertEqual(None, self.author.entry_nice)

        # Entry with low vote rate
        entry = Entry.objects.create(**self.entry_base)
        del self.author.entry_nice
        cache.clear()

        self.assertEqual(None, self.author.entry_nice)

        # Entry with enough vote rate
        entry.vote_rate = Decimal("1.1")
        entry.save()

        del self.author.entry_nice
        cache.clear()
        self.assertEqual(entry, self.author.entry_nice)


class CategoryModelTests(TransactionTestCase):
    @classmethod
    def setUp(cls):
        cls.category = Category.objects.create(name="şeker")

    def test_absolute_url(self):
        absolute_url = reverse("topic_list", kwargs={"slug": self.category.slug})
        self.assertEqual(absolute_url, self.category.get_absolute_url())

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="şeker")

        similar_category = Category.objects.create(name="seker")
        self.assertNotEqual(similar_category.slug, self.category.slug)

    def test_str(self):
        self.assertEqual(str(self.category), self.category.name)


class EntryModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(username="user", email="0")
        cls.topic = Topic.objects.create_topic("test_topic")
        cls.entry_base = {"topic": cls.topic, "author": cls.author}
        cls.entry = Entry.objects.create(**cls.entry_base, content="CONtent İŞçI")

    def test_absolute_url(self):
        absolute_url = reverse("entry-permalink", kwargs={"entry_id": self.entry.pk})
        self.assertEqual(absolute_url, self.entry.get_absolute_url())

    def test_content_lower(self):
        self.assertEqual("content işçı", self.entry.content)

    def test_topic_ownership(self):
        self.assertEqual(self.author, self.topic.created_by)

        topic_with_no_ownership = Topic.objects.create_topic("test_topic2")
        self.assertIsNone(topic_with_no_ownership.created_by)

        new_entry = Entry.objects.create(author=self.author, topic=topic_with_no_ownership, is_draft=True)
        self.assertIsNone(topic_with_no_ownership.created_by)

        new_entry.is_draft = False
        new_entry.save()
        self.assertEqual(self.author, topic_with_no_ownership.created_by)

    def test_str(self):
        self.assertEqual(str(self.entry), f"{self.entry.id}#{self.entry.author}")

    def test_votes(self):
        # Initial vote should be 0
        self.assertEqual(self.entry.vote_rate.conjugate(), Decimal("0"))

        # Increase by .2
        self.entry.update_vote(Decimal(".2"))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.vote_rate, Decimal(".2"))

        # Increase by .2 again to ensure that it is incremental (not a replacement)
        self.entry.update_vote(Decimal(".2"))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.vote_rate, Decimal(".4"))

        # Increase by -.2 (decrease .2)
        self.entry.update_vote(Decimal("-.2"))
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.vote_rate, Decimal(".2"))

        # Increase by change
        self.entry.update_vote(Decimal(".2"), change=True)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.vote_rate, Decimal(".6"))


class MementoModelTests(TransactionTestCase):
    @classmethod
    def setUp(cls):
        cls.author_1 = Author.objects.create(username="user1", email="1")
        cls.author_2 = Author.objects.create(username="user2", email="2")

    def test_unique_constraint(self):
        Memento.objects.create(holder=self.author_1, patient=self.author_2)

        # Make sure that the fields are evaluated differently
        Memento.objects.create(holder=self.author_2, patient=self.author_1)

        # Creating a non-unique object
        with self.assertRaises(IntegrityError):
            Memento.objects.create(holder=self.author_1, patient=self.author_2)

    def test_str(self):
        memento = Memento.objects.create(holder=self.author_1, patient=self.author_2)
        self.assertEqual(str(memento), f"Memento#1, from {self.author_1} about {self.author_2}")


class UserVerificationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(username="user", email="0")

    def test_no_multiple_verifications(self):
        UserVerification.objects.create(author=self.author, expiration_date=timezone.now())
        latest_uv = UserVerification.objects.create(author=self.author, expiration_date=timezone.now())
        list_uv_for_author = UserVerification.objects.filter(author=self.author)
        self.assertEqual(list_uv_for_author.count(), 1)
        self.assertEqual(latest_uv, list_uv_for_author.first())

    def test_email_confirmed_status(self):
        # For profile page email change status indicator
        # Create pending email confirmation
        uv_author = UserVerification.objects.create(
            author=self.author, expiration_date=timezone.now() + datetime.timedelta(hours=12)
        )
        self.assertEqual(self.author.email_confirmed, False)

        # No pending email confirmation
        uv_author.delete()
        self.assertEqual(self.author.email_confirmed, True)

        # There is a email confirmation sent, but it has been expired
        UserVerification.objects.create(
            author=self.author, expiration_date=timezone.now() - datetime.timedelta(hours=30)
        )
        self.assertEqual(self.author.email_confirmed, True)


class MessageModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.generic_superuser = Author.objects.create(
            username=settings.GENERIC_SUPERUSER_USERNAME, email="gsu", is_active=True
        )
        cls.author_1 = Author.objects.create(username="user1", email="1", is_active=True)
        cls.author_2 = Author.objects.create(username="user2", email="2", is_active=True)

    def test_read_at_time(self):
        some_message = Message.objects.compose(self.author_1, self.author_2, "body")
        self.assertIsNone(some_message.read_at)
        some_message.mark_read()
        self.assertIsNotNone(some_message.read_at)

    def test_str(self):
        some_message = Message.objects.compose(self.author_1, self.author_2, "body")
        self.assertEqual(str(some_message), "1")


class ConversationModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.generic_superuser = Author.objects.create(
            username=settings.GENERIC_SUPERUSER_USERNAME, email="gsu", is_active=True
        )
        cls.author_1 = Author.objects.create(username="user1", email="1", is_active=True)
        cls.author_2 = Author.objects.create(username="user2", email="2", is_active=True)

    def test_conversation_creation_on_messaging(self):
        # Check initial status
        conversation_count = Conversation.objects.all().count()
        self.assertEqual(conversation_count, 0)

        # A conversation started
        some_msg = Message.objects.compose(self.author_1, self.author_2, "gelmiyorsun artık günah çıkarmaya?")

        conversation_count = Conversation.objects.all().count()
        self.assertEqual(conversation_count, 2)

        # Get that conversation and check if the previous message is in it
        current_conversation_1_2 = Conversation.objects.get(holder=self.author_1, target=self.author_2)
        current_conversation_2_1 = Conversation.objects.get(holder=self.author_2, target=self.author_1)
        self.assertIn(some_msg, current_conversation_1_2.messages.all())
        self.assertIn(some_msg, current_conversation_2_1.messages.all())

        # Reply message, check also if that message in conversation and check no extra conversation is created
        # for it (it should append to newly created conversation)

        some_other_msg = Message.objects.compose(self.author_2, self.author_1, "işlemiyorum ki, evdeyim hep.")
        conversation_count = Conversation.objects.all().count()
        self.assertEqual(conversation_count, 2)
        self.assertIn(some_other_msg, current_conversation_1_2.messages.all())
        self.assertIn(some_other_msg, current_conversation_2_1.messages.all())

        # Check participants
        self.assertEqual(self.author_1, current_conversation_1_2.holder)
        self.assertEqual(self.author_1, current_conversation_2_1.target)
        self.assertEqual(self.author_2, current_conversation_2_1.holder)
        self.assertEqual(self.author_2, current_conversation_1_2.target)

    def test_last_message(self):
        some_msg = Message.objects.compose(self.author_1, self.author_2, "baapoçun çen?!!")
        current_conversation_1_2 = Conversation.objects.get(holder=self.author_1, target=self.author_2)
        current_conversation_2_1 = Conversation.objects.get(holder=self.author_2, target=self.author_1)
        self.assertEqual(some_msg, current_conversation_1_2.last_message)
        self.assertEqual(some_msg, current_conversation_2_1.last_message)

        time.sleep(0.01)  # apparently auto_now_add fields will be exactly the same in the same block.
        some_other_msg = Message.objects.compose(self.author_1, self.author_2, "ya bi sktr git allah allah")
        self.assertEqual(some_other_msg, current_conversation_1_2.last_message)
        self.assertEqual(some_other_msg, current_conversation_2_1.last_message)

    def test_str(self):
        Message.objects.compose(self.author_1, self.author_2, "baapoçun çen?!!")
        current_conversation = Conversation.objects.get(holder=self.author_1, target=self.author_2)
        self.assertEqual(str(current_conversation), "<Conversation> holder-> user1, target-> user2")


class GeneralReportModelTest(TestCase):
    def test_str(self):
        report = GeneralReport.objects.create(subject="subject")
        self.assertEqual(str(report), "subject <GeneralReport>#1")


class TopicModelTest(TransactionTestCase):
    @classmethod
    def setUp(cls):
        cls.some_topic = Topic.objects.create_topic("zeki müren")
        cls.author = Author.objects.create(username="user", email="0", is_novice=False)

    def test_uniqueness(self):
        with self.assertRaises(IntegrityError):
            Topic.objects.create_topic("zeki müren")

        similar_topic = Topic.objects.create_topic("zeki muren")
        self.assertNotEqual(similar_topic.slug, self.some_topic.slug)

    def test_existence(self):
        self.assertEqual(self.some_topic.exists, True)

    def test_valid(self):
        self.assertEqual(self.some_topic.valid, True)

    def test_has_entries(self):
        # Initial status
        self.assertEqual(self.some_topic.has_entries, False)

        # Add non-published entry
        Entry.objects.create(topic=self.some_topic, author=self.author, is_draft=True)
        self.assertEqual(self.some_topic.has_entries, False)

        # Add published entry
        Entry.objects.create(topic=self.some_topic, author=self.author)
        self.assertEqual(self.some_topic.has_entries, True)

    def test_follow_check(self):
        # Initial status
        self.assertEqual(self.some_topic.follow_check(self.author), False)

        # Follow
        TopicFollowing.objects.create(topic=self.some_topic, author=self.author)
        self.assertEqual(self.some_topic.follow_check(self.author), True)

    def test_title_lower(self):
        weird_topic = Topic.objects.create_topic("wEİIrdo")
        self.assertEqual("weiırdo", weird_topic.title)

    def test_absolute_url(self):
        absolute_url = reverse("topic", kwargs={"slug": self.some_topic.slug})
        self.assertEqual(absolute_url, self.some_topic.get_absolute_url())

    def test_str(self):
        self.assertEqual(str(self.some_topic), "zeki müren")
