from django.shortcuts import get_object_or_404

from ..models import Entry
from ..utils.settings import VOTE_RATES
from ..utils.views import JsonView


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
        decrease, increase = VOTE_RATES["reduce"], VOTE_RATES["increase"]

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
                    entry.update_vote(decrease * k)
                elif cast_down:
                    entry.update_vote(increase * k)
            else:
                # Changes the vote cast.
                if cast_up:
                    entry.update_vote(increase * k, change=True)
                if cast_down:
                    entry.update_vote(decrease * k, change=True)
        else:
            # First time voting.
            if cast_up:
                entry.update_vote(increase * k)
            elif cast_down:
                entry.update_vote(decrease * k)

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
