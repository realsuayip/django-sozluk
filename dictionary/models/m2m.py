from django.db import models


class TopicFollowing(models.Model):
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE)
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
    date_created = models.DateTimeField(auto_now_add=True)


class EntryFavorites(models.Model):
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    entry = models.ForeignKey("Entry", on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)


class UpvotedEntries(models.Model):
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    entry = models.ForeignKey("Entry", on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)


class DownvotedEntries(models.Model):
    author = models.ForeignKey("Author", on_delete=models.CASCADE)
    entry = models.ForeignKey("Entry", on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)
