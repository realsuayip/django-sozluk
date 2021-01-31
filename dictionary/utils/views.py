from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.paginator import EmptyPage, Paginator
from django.views.generic import View

from dictionary.utils.mixins import IntermediateActionMixin


class IntermediateActionView(PermissionRequiredMixin, IntermediateActionMixin, View):
    pass


class SafePaginator(Paginator):
    """
    Yields last page if the provided page is bigger than the total number of pages.
    """

    def validate_number(self, number):
        try:
            return super().validate_number(number)
        except EmptyPage:
            if number > 1:
                return self.num_pages
            raise
