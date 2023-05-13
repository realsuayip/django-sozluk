from django.db import models
from django.db.models import Subquery


class SubQueryCount(Subquery):
    template = "(SELECT count(*) FROM (%(subquery)s) _count)"
    output_field = models.IntegerField()
