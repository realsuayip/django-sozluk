from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy

from ..models import Author, Entry, Category, Topic, TopicFollowing, Message
from ..utils.managers import TopicListManager
from ..utils.settings import YEAR_RANGE, VOTE_RATES, TOPICS_PER_PAGE_DEFAULT, LOGIN_REQUIRED_CATEGORIES
from ..utils.views import JsonView


class AsyncTopicList(JsonView):
    http_method_names = ['get']

    def handle(self):
        slug = self.kwargs.get("slug")

        if slug in LOGIN_REQUIRED_CATEGORIES and not self.request.user.is_authenticated:
            return self.error(status=403)

        year = self.request_data.get("year") if slug == "tarihte-bugun" else None
        page = self.request_data.get("page")
        search_keys = self.request_data if slug == "hayvan-ara" else None
        fetch_cached = self.request_data.get("nocache") != "yes"
        paginate_by = TOPICS_PER_PAGE_DEFAULT

        if self.request.user.is_authenticated:
            paginate_by = self.request.user.topics_per_page

        if year:
            try:
                if int(year) not in YEAR_RANGE:
                    return self.bad_request()
            except(ValueError, OverflowError):
                return self.bad_request()

        manager = TopicListManager(self.request.user, slug, year, fetch_cached, search_keys)
        paginated = Paginator(manager.serialized, paginate_by)
        topic_data = paginated.get_page(page).object_list
        self.data = dict(topic_data=topic_data, refresh_count=manager.refresh_count,
                         slug_identifier=manager.slug_identifier, total_pages=paginated.num_pages)

        return super().handle()


class AutoComplete(JsonView):
    http_method_names = ['get']

    def handle(self):
        if self.request_data.get("author"):
            self.data = self.author()
        elif self.request_data.get("query"):
            self.data = self.query()

        return super().handle()

    def author(self):
        objects = Author.objects.filter(username__istartswith=self.request_data.get("author"))
        response = [obj.username for obj in objects]
        return dict(suggestions=response)

    def query(self):
        query = self.request_data.get("query")

        if query.startswith("@"):
            if len(query) <= 1:
                response = ["@"]
            else:
                response = ["@" + obj.username for obj in Author.objects.filter(username__istartswith=query[1:])[:7]]
        else:
            response = [obj.title for obj in Topic.objects_published.filter(title__istartswith=query)[:7]]

            for extra in Topic.objects_published.filter(title__icontains=query)[:7]:
                if len(response) >= 7:
                    break
                if extra.title not in response:
                    response.append(extra.title)

            extra_authors = Author.objects.filter(username__istartswith=query)[:3]
            for author in extra_authors:
                response.append("@" + author.username)
        return dict(suggestions=response)


class UserAction(LoginRequiredMixin, JsonView):
    http_method_names = ['post']

    sender = None
    recipient = None

    def handle(self):
        action = self.request_data.get("type")
        self.sender = self.request.user
        self.recipient = get_object_or_404(Author, username=self.request_data.get("recipient_username"))

        if self.sender == self.recipient:
            return self.bad_request()

        if action == "follow":
            return self.follow()

        if action == "block":
            return self.block()

        return super().handle()

    def follow(self):
        sender, recipient = self.sender, self.recipient

        if sender in recipient.blocked.all() or recipient in sender.blocked.all():
            return self.bad_request()

        if recipient in sender.following.all():
            sender.following.remove(recipient)
        else:
            sender.following.add(recipient)
        return self.success()

    def block(self):
        sender, recipient = self.sender, self.recipient

        if recipient in sender.blocked.all():
            sender.blocked.remove(recipient)
            return self.success()

        if recipient in sender.following.all():
            sender.following.remove(recipient)

        if sender in recipient.following.all():
            recipient.following.remove(sender)

        sender.blocked.add(recipient)
        return self.success(redirect_url=self.request.build_absolute_uri(reverse("home")))


class EntryAction(LoginRequiredMixin, JsonView):
    http_method_names = ['get', 'post']
    owner_action = False
    redirect_url = None
    entry = None
    success_message = "oldu bu iş"

    def handle(self):
        action = self.request_data.get("type")

        try:
            self.entry = get_object_or_404(Entry, id=int(self.request_data.get("entry_id")))
        except (ValueError, TypeError, Entry.DoesNotExist):
            return self.bad_request()

        self.owner_action = self.entry.author == self.request.user
        self.redirect_url = reverse_lazy("topic", kwargs={"slug": self.entry.topic.slug}) if self.request_data.get(
            "redirect") == "true" else None

        if action == "delete":
            self.success_message = "silindi"
            return self.delete()

        if action == "pin":
            return self.pin()

        if action == "favorite":
            self.data = self.favorite()

        if action == "favorite_list":
            self.data = self.favorite_list()

        return super().handle()

    def delete(self):
        if self.owner_action:
            self.entry.delete()
            if self.redirect_url:
                return self.success(message_pop=True, redirect_url=self.redirect_url)
            return self.success()

        return self.error()

    def pin(self):
        if self.owner_action:
            if self.request.user.pinned_entry == self.entry:  # unpin
                self.request.user.pinned_entry = None
            else:
                self.request.user.pinned_entry = self.entry
            self.request.user.save()
            return self.success()
        return self.error()

    def favorite(self):
        if self.entry in self.request.user.favorite_entries.all():
            self.request.user.favorite_entries.remove(self.entry)
            self.entry.update_vote(VOTE_RATES["reduce"])
            status = -1
        else:
            self.request.user.favorite_entries.add(self.entry)
            self.entry.update_vote(VOTE_RATES["increase"])
            status = 1

        return dict(count=self.entry.favorited_by.count(), status=status)

    def favorite_list(self):
        users_favorited = self.entry.favorited_by.all()
        authors, novices = [], []
        for user in users_favorited:
            if user.is_novice:
                novices.append(user.username)
            else:
                authors.append(user.username)
        return dict(users=[authors, novices])


class TopicAction(LoginRequiredMixin, JsonView):
    http_method_names = ['post']
    topic_object = None

    def handle(self):
        action = self.request_data.get("type")

        try:
            self.topic_object = get_object_or_404(Topic, id=int(self.request_data.get("topic_id")))
        except (ValueError, TypeError, Topic.DoesNotExist):
            return self.bad_request()

        if action == "follow":
            return self.follow()

        return super().handle()

    def follow(self):
        try:
            # unfollow if already following
            existing = TopicFollowing.objects.get(topic=self.topic_object, author=self.request.user)
            existing.delete()
        except TopicFollowing.DoesNotExist:
            TopicFollowing.objects.create(topic=self.topic_object, author=self.request.user)
        return self.success()


class CategoryAction(LoginRequiredMixin, JsonView):
    http_method_names = ["post"]
    category_object = None

    def handle(self):
        action = self.request_data.get("type")

        try:
            self.category_object = Category.objects.get(pk=int(self.request_data.get("category_id")))
        except (ValueError, OverflowError, Category.DoesNotExist):
            return self.bad_request()

        if action in ["follow"]:
            return self.follow()

        return self.bad_request()

    def follow(self):
        if self.category_object in self.request.user.following_categories.all():
            self.request.user.following_categories.remove(self.category_object)
        else:
            self.request.user.following_categories.add(self.category_object)

        manager = TopicListManager(self.request.user, "bugun")
        manager.delete_cache()
        return self.success()


class ComposeMessage(LoginRequiredMixin, JsonView):
    http_method_names = ['post']

    def handle(self):
        return self.compose()

    def compose(self):
        message_body = self.request_data.get("message_body")
        if len(message_body) < 3:
            self.error_message = "az bir şeyler yaz yeğenim"
            return self.error(status=200)

        try:
            recipient = Author.objects.get(username=self.request_data.get("recipient"))
        except Author.DoesNotExist:
            self.error_message = "öyle birini bulamadım valla"
            return self.error(status=200)

        msg = Message.objects.compose(self.request.user, recipient, message_body)

        if not msg:
            self.error_message = "mesajınızı gönderemedik ne yazık ki"
            return self.error(status=200)

        self.success_message = "mesajınız sağ salim gönderildi"
        return self.success()


class Vote(JsonView):
    """
    Anonymous users can vote, in order to hinder duplicate votings, session is used; though it is not
    the best way to handle this, I think it's better than storing all the IP adresses of the guest users as acquiring an
    IP adress is a nuance; it depends on the server and it can also be manipulated by keen hackers. It's just better to
    stick to this way instead of making things complicated as there is no way to make this work 100% intended.
    """
    http_method_names = ['post']

    # View specific attributes
    vote = None
    entry = None
    already_voted = False
    already_voted_type = None
    anonymous = True
    anon_votes = None
    cast_up = None
    cast_down = None

    def handle(self):
        self.vote = self.request_data.get("vote")
        self.cast_up = self.vote == "up"
        self.cast_down = self.vote == "down"

        try:
            self.entry = get_object_or_404(Entry, id=int(self.request_data.get("entry_id")))
        except (ValueError, OverflowError):
            return self.error()

        if self.request.user.is_authenticated:
            # self-vote not allowed
            if self.request.user == self.entry.author:
                return self.error()
            self.anonymous = False

        if self.vote in ["up", "down"]:
            if self.cast():
                return self.success()

        return super().handle()

    def cast(self):
        entry, cast_up, cast_down = self.entry, self.cast_up, self.cast_down
        reduce, increase = VOTE_RATES["reduce"], VOTE_RATES["increase"]

        if self.anonymous:
            k = VOTE_RATES["anonymous_multiplier"]
            self.anon_votes = self.request.session.get("anon_votes")
            if self.anon_votes:
                for record in self.anon_votes:  # do not use the name 'record' method's this scope
                    if record.get("entry_id") == entry.id:
                        self.already_voted = True
                        self.already_voted_type = record.get("type")
                        break
        else:
            k = VOTE_RATES["authenticated_multiplier"]
            sender = self.request.user
            if entry in sender.upvoted_entries.all():
                self.already_voted = True
                self.already_voted_type = "up"
            elif entry in sender.downvoted_entries.all():
                self.already_voted = True
                self.already_voted_type = "down"

        if self.already_voted:
            if self.already_voted_type == self.vote:
                # Removes the vote cast.
                if cast_up:
                    entry.update_vote(reduce * k)
                elif cast_down:
                    entry.update_vote(increase * k)
            else:
                # Changes the vote cast.
                if cast_up:
                    entry.update_vote(increase * k, change=True)
                if cast_down:
                    entry.update_vote(reduce * k, change=True)
        else:
            # First time voting.
            if cast_up:
                entry.update_vote(increase * k)
            elif cast_down:
                entry.update_vote(reduce * k)

        if self.record_vote():
            return True
        return False

    def record_vote(self):
        entry, cast_up, cast_down = self.entry, self.cast_up, self.cast_down
        prior_cast_up = self.already_voted_type == "up"
        prior_cast_down = self.already_voted_type == "down"

        if self.anonymous:
            anon_votes_new = []
            if self.already_voted:
                anon_votes_new = [y for y in self.anon_votes if y.get('entry_id') != entry.id]
                if self.already_voted_type != self.vote:
                    anon_votes_new.append({"entry_id": entry.id, "type": self.vote})
            else:
                if self.anon_votes:
                    self.anon_votes.append({"entry_id": entry.id, "type": self.vote})
                    anon_votes_new = self.anon_votes
                else:
                    anon_votes_new.append({"entry_id": entry.id, "type": self.vote})

            self.request.session["anon_votes"] = anon_votes_new

        else:
            sender = self.request.user
            if self.already_voted:
                if prior_cast_up and cast_up:
                    sender.upvoted_entries.remove(entry)
                elif prior_cast_down and cast_down:
                    sender.downvoted_entries.remove(entry)
                elif prior_cast_up and cast_down:
                    sender.upvoted_entries.remove(entry)
                    sender.downvoted_entries.add(entry)
                elif prior_cast_down and cast_up:
                    sender.downvoted_entries.remove(entry)
                    sender.upvoted_entries.add(entry)
            else:
                if cast_up:
                    sender.upvoted_entries.add(entry)
                elif cast_down:
                    sender.downvoted_entries.add(entry)
        return True
