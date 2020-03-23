from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import View

from .mixins import IntermediateActionMixin


class IntermediateActionView(PermissionRequiredMixin, IntermediateActionMixin, View):
    pass
