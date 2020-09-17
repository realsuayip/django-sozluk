from django.http import Http404
from django.test import TestCase, TransactionTestCase

from dictionary.conf import settings
from dictionary.models import Author, Entry, Conversation, Message, Topic


class EntryModelManagersTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.topic = Topic.objects.create_topic("topik")
        cls.author = Author.objects.create(username="author", email="0", is_novice=False)
        cls.novice = Author.objects.create(username="novice", email="1")

        cls.author_eb = {"topic": cls.topic, "author": cls.author}
        cls.novice_eb = {"topic": cls.topic, "author": cls.novice}

        cls.entry_by_author = Entry.objects.create(**cls.author_eb)
        cls.entry_by_novice = Entry.objects.create(**cls.novice_eb)

        cls.entry_by_author_draft = Entry.objects.create(**cls.author_eb, is_draft=True)
        cls.entry_by_novice_draft = Entry.objects.create(**cls.novice_eb, is_draft=True)

    def test_objects(self):
        # Published AND Non-novice entries
        queryset = Entry.objects.all()

        self.assertEqual(1, queryset.count())
        self.assertIn(self.entry_by_author, queryset)

    def test_objects_all(self):
        # ALL entries
        queryset = Entry.objects_all.all()

        self.assertEqual(4, queryset.count())
        self.assertIn(self.entry_by_author, queryset)
        self.assertIn(self.entry_by_novice, queryset)
        self.assertIn(self.entry_by_author_draft, queryset)
        self.assertIn(self.entry_by_novice_draft, queryset)

    def test_objects_published(self):
        # Only published entries (non-novice entries included)
        queryset = Entry.objects_published.all()

        self.assertEqual(2, queryset.count())
        self.assertIn(self.entry_by_author, queryset)
        self.assertIn(self.entry_by_novice, queryset)


class ConversationModelManagersTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.generic_superuser = Author.objects.create(
            username=settings.GENERIC_SUPERUSER_USERNAME, email="gsu", is_active=True
        )
        cls.author_1 = Author.objects.create(username="a1", email="1", is_active=True)
        cls.author_2 = Author.objects.create(username="a2", email="2", is_active=True)
        cls.author_3 = Author.objects.create(username="a3", email="3", is_active=True)
        cls.author_4 = Author.objects.create(username="a4", email="4", is_active=True)

        author_5 = Author.objects.create(username="a5", email="5", is_active=True)
        author_6 = Author.objects.create(username="a6", email="7", is_active=True)
        author_7 = Author.objects.create(username="a8", email="8", is_active=True)

        cls.convo_1_2_msg = Message.objects.compose(cls.author_1, cls.author_2, "domates")
        Message.objects.compose(cls.author_1, cls.author_3, "biber")
        Message.objects.compose(cls.author_2, cls.author_3, "patlıcan")

        Message.objects.compose(cls.author_4, author_5, "filiz")
        Message.objects.compose(cls.author_4, author_6, "filiz")
        Message.objects.compose(cls.author_4, author_7, "önemsiz")

        cls.conversation_1_2 = Conversation.objects.get(holder=cls.author_1, target=cls.author_2)
        cls.conversation_2_1 = Conversation.objects.get(holder=cls.author_2, target=cls.author_1)

        cls.conversation_1_3 = Conversation.objects.get(holder=cls.author_1, target=cls.author_3)
        cls.conversation_3_1 = Conversation.objects.get(holder=cls.author_3, target=cls.author_1)

        cls.conversation_2_3 = Conversation.objects.get(holder=cls.author_2, target=cls.author_3)
        cls.conversation_3_2 = Conversation.objects.get(holder=cls.author_3, target=cls.author_2)

        cls.conversation_4_5 = Conversation.objects.get(holder=cls.author_4, target=author_5)
        cls.conversation_5_4 = Conversation.objects.get(holder=author_5, target=cls.author_4)

        cls.conversation_4_6 = Conversation.objects.get(holder=cls.author_4, target=author_6)
        cls.conversation_6_4 = Conversation.objects.get(holder=author_6, target=cls.author_4)

        cls.conversation_4_7 = Conversation.objects.get(holder=cls.author_4, target=author_7)
        cls.conversation_7_4 = Conversation.objects.get(holder=author_7, target=cls.author_4)

    def test_list_for_user_with_no_search_term(self):
        conversation_list = Conversation.objects.list_for_user(self.author_1)
        self.assertEqual(2, conversation_list.count())
        self.assertIn(self.conversation_1_2, conversation_list)
        self.assertIn(self.conversation_1_3, conversation_list)

        conversation_list_2 = Conversation.objects.list_for_user(self.author_3)
        self.assertEqual(2, conversation_list.count())
        self.assertIn(self.conversation_3_1, conversation_list_2)
        self.assertIn(self.conversation_3_2, conversation_list_2)

        conversation_list_3 = Conversation.objects.list_for_user(self.author_4)
        self.assertEqual(3, conversation_list_3.count())
        self.assertIn(self.conversation_4_5, conversation_list_3)
        self.assertIn(self.conversation_4_6, conversation_list_3)
        self.assertIn(self.conversation_4_7, conversation_list_3)

    def test_list_for_user_with_search_term(self):
        # Search by message content
        conversation_list = Conversation.objects.list_for_user(self.author_1, search_term="domates")
        self.assertEqual(1, conversation_list.count())
        self.assertIn(self.conversation_1_2, conversation_list)

        conversation_list_4 = Conversation.objects.list_for_user(self.author_4, search_term="filiz")
        self.assertEqual(2, conversation_list_4.count())
        self.assertIn(self.conversation_4_5, conversation_list_4)
        self.assertIn(self.conversation_4_6, conversation_list_4)

        # Search by author nick
        conversation_list_2 = Conversation.objects.list_for_user(self.author_2, search_term="a3")
        self.assertEqual(1, conversation_list_2.count())
        self.assertIn(self.conversation_2_3, conversation_list_2)

        # Keyword with no result
        conversation_list_3 = Conversation.objects.list_for_user(self.author_3, search_term="avakado")
        self.assertEqual(0, conversation_list_3.count())

    def test_with_user(self):
        # Self-conversation is not allowed
        self_convo = Conversation.objects.with_user(self.author_1, self.author_1)
        self.assertIsNone(self_convo)

        conversation_1_2 = Conversation.objects.with_user(self.author_1, self.author_2)
        self.assertEqual(conversation_1_2, self.conversation_1_2)

        # Test non-interchangeability
        conversation_1_2_alternative_call = Conversation.objects.with_user(self.author_2, self.author_1)
        self.assertNotEqual(conversation_1_2, conversation_1_2_alternative_call)

        # Test messages
        conversation_1_2_messages = conversation_1_2.messages.all()
        self.assertEqual(1, conversation_1_2_messages.count())
        self.assertIn(self.convo_1_2_msg, conversation_1_2_messages)


class TopicModelManagersTest(TransactionTestCase):
    @classmethod
    def setUp(cls):
        cls.author = Author.objects.create(username="user666", email="666", is_novice=False)
        cls.novice = Author.objects.create(username="user333", email="333")

        cls.topic_1 = Topic.objects.create_topic("şeker çocuk", created_by=cls.author)  # slug -> seker-cocuk
        cls.topic_2 = Topic.objects.create_topic("tepeleme")  # slug -> tepeleme

        cls.entry_1 = Entry.objects.create(author=cls.author, topic=cls.topic_1, is_draft=True)
        cls.entry_2 = Entry.objects.create(author=cls.author, topic=cls.topic_2)

        # Non draft, by novice (for test_manager_published)
        Entry.objects.create(author=cls.novice, topic=cls.topic_1)

    def test_create_topic(self):
        # Just writing this test to inform the user (that he may have been messed up with this method)
        topic_1 = Topic.objects.get(pk=1)
        self.assertEqual(topic_1, self.topic_1)
        self.assertEqual(topic_1.created_by, self.author)

    def test_get_or_pseudo(self):
        # Non-existent slug
        no_slug = Topic.objects.get_or_pseudo(slug="engIİn ")
        self.assertEqual(False, no_slug.exists)
        self.assertEqual("engıin", no_slug.title)
        self.assertEqual(str(no_slug), "<PseudoTopic engıin>")

        # Non-existent unicode_string
        no_unicode = Topic.objects.get_or_pseudo(unicode_string="şeker adam")
        self.assertEqual(False, no_unicode.exists)
        self.assertEqual("şeker adam", no_unicode.title)

        # Non-existent entry_id
        with self.assertRaises(Http404):
            Topic.objects.get_or_pseudo(entry_id=36693)

        # Existent slug
        yes_slug = Topic.objects.get_or_pseudo(slug="seker-cocuk")
        self.assertEqual(True, yes_slug.exists)
        self.assertEqual("şeker çocuk", yes_slug.title)
        self.assertEqual("seker-cocuk", yes_slug.slug)

        # Existent unicode_string
        yes_unicode = Topic.objects.get_or_pseudo(unicode_string="şeker çocuk")
        self.assertEqual(True, yes_unicode.exists)
        self.assertEqual("şeker çocuk", yes_unicode.title)
        self.assertEqual("seker-cocuk", yes_unicode.slug)

        # Existent entry_id (published)
        yes_entry = Topic.objects.get_or_pseudo(entry_id=self.entry_2.pk)
        self.assertEqual(True, yes_entry.exists)
        self.assertEqual("tepeleme", yes_entry.title)
        self.assertEqual("tepeleme", yes_entry.slug)

        # Existent entry_id (not published)
        with self.assertRaises(Http404):
            Topic.objects.get_or_pseudo(entry_id=self.entry_1.pk)

        # No argument
        with self.assertRaises(ValueError):
            Topic.objects.get_or_pseudo()

    def test_manager_published(self):
        # Only 1 suitable topic object created in topic
        topics = Topic.objects_published.all()
        self.assertEqual(1, topics.count())
        self.assertIn(self.topic_2, topics)
