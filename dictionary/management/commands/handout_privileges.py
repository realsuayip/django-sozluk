from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from ...models import Author
from ...utils.settings import SUGGESTIONS_ENTRY_REQUIREMENT


class Command(BaseCommand):
    """
    Give some privileges to users.
    """

    def handle(self, **options):
        perm = Permission.objects.get(codename="can_suggest_categories")

        authors = (
            Author.objects_accessible.exclude(Q(user_permissions__in=[perm]) | Q(is_novice=True))
            .annotate(count=Count("entry", filter=Q(entry__is_draft=False)))
            .filter(count__gte=SUGGESTIONS_ENTRY_REQUIREMENT)
        )

        for author in authors:
            author.user_permissions.add(perm)
