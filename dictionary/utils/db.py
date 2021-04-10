from django.db import models
from django.db.models import Subquery


class SubQueryCount(Subquery):  # noqa
    template = "(SELECT count(*) FROM (%(subquery)s) _count)"
    output_field = models.IntegerField()
