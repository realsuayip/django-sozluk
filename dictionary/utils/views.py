from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import View

from dictionary.utils.mixins import IntermediateActionMixin


class IntermediateActionView(PermissionRequiredMixin, IntermediateActionMixin, View):
    pass
