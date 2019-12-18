import datetime

from django.test import TestCase
from django.utils import timezone

import mock

from ..models import Author, Entry, Topic, Message, Category


class AuthorModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(username="user", email="0")
        cls.topic = Topic.objects.create_topic("test_topic")
        cls.entry_base = dict(topic=cls.topic, author=cls.author)

    def test_profile_entry_counts(self):
        Entry.objects.create(**self.entry_base)  # created now (today)
        # dates to be mocked for auto now add field 'date_created'
        mock_60 = timezone.now() - datetime.timedelta(days=35)  # created more than 1 months ago
        mock_30 = timezone.now() - datetime.timedelta(days=25)  # created in 1 month period
        mock_14 = timezone.now() - datetime.timedelta(days=12)  # created in 2 weeks period
        mock_7 = timezone.now() - datetime.timedelta(days=5)  # created in 1 week period
        mock_1 = timezone.now() - datetime.timedelta(hours=20)  # created today

        with mock.patch('django.utils.timezone.now') as mock_now:
            mock_now.return_value = mock_60
            Entry.objects.create(**self.entry_base)
            mock_now.return_value = mock_30
            Entry.objects.create(**self.entry_base)
            mock_now.return_value = mock_14
            Entry.objects.create(**self.entry_base)
            mock_now.return_value = mock_7
            Entry.objects.create(**self.entry_base)
            mock_now.return_value = mock_1
            Entry.objects.create(**self.entry_base)

        self.assertEqual(self.author.entry_count, 6)
        self.assertEqual(self.author.entry_count_day, 2)
        self.assertEqual(self.author.entry_count_month, 5)
        self.assertEqual(self.author.entry_count_week, 3)

    def test_last_entry_date(self):
        Entry.objects.create(**self.entry_base, is_draft=True)
        self.assertIsNone(self.author.last_entry_date)
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
        10 published entries needed in order an user to be in the novice list, if the number of entries drop to < 10
        user is removed from novice list
        """

        # Initial status
        self.assertEqual(self.author.application_status, Author.ON_HOLD)
        self.assertIsNone(self.author.application_date)

        # Add NINE entries
        for _ in range(9):
            Entry.objects.create(**self.entry_base)

        # add an entry which is a draft
        Entry.objects.create(**self.entry_base, is_draft=True)

        # There are 10 PUBLISHED entries required, 9 present, so everything should be the same
        self.assertEqual(self.author.application_status, Author.ON_HOLD)
        self.assertIsNone(self.author.application_date)

        # add 10th entry (user joins the novice list)
        final_entry = Entry.objects.create(**self.entry_base)

        self.assertEqual(self.author.application_status, Author.PENDING)
        self.assertIsNotNone(self.author.application_date)

        final_entry.delete()  # delete 10th entry to retreat from novice list

        self.assertEqual(self.author.application_status, Author.ON_HOLD)
        self.assertIsNone(self.author.application_date)

    def test_message_preferences(self):
        some_author = Author.objects.create(username="author", email="3", is_novice=False)
        some_novice = Author.objects.create(username="novice", email="4")

        # ALL users (database default)
        msg_sent_by_novice = Message.objects.compose(some_novice, self.author, "test")
        msg_sent_by_author = Message.objects.compose(some_author, self.author, "test")
        self.assertNotEqual(msg_sent_by_author, False)
        self.assertNotEqual(msg_sent_by_novice, False)

        # Disabled
        self.author.message_preference = Author.DISABLED
        msg_sent_by_novice = Message.objects.compose(some_novice, self.author, "test")
        msg_sent_by_author = Message.objects.compose(some_author, self.author, "test")
        self.assertEqual(msg_sent_by_author, False)
        self.assertEqual(msg_sent_by_novice, False)

        # Authors (non-novices) only
        self.author.message_preference = Author.AUTHOR_ONLY
        msg_sent_by_novice = Message.objects.compose(some_novice, self.author, "test")
        msg_sent_by_author = Message.objects.compose(some_author, self.author, "test")
        self.assertNotEqual(msg_sent_by_author, False)
        self.assertEqual(msg_sent_by_novice, False)

        # Following only
        self.author.message_preference = Author.FOLLOWING_ONLY
        msg_sent_by_non_follower = Message.objects.compose(some_author, self.author, "test")
        self.assertEqual(msg_sent_by_non_follower, False)
        self.author.following.add(some_author)  # add following to send message
        msg_sent_by_follower = Message.objects.compose(some_author, self.author, "test")
        self.assertNotEqual(msg_sent_by_follower, False)

    def test_follow_all_categories_on_creation(self):
        category_1 = Category.objects.create(name="test")
        Category.objects.create(name="test2")
        some_user = Author.objects.create(username="some_user", email="5")
        self.assertIn(category_1, some_user.following_categories.all())
        self.assertEqual(some_user.following_categories.all().count(), 2)
