from django.contrib import admin, messages as notifications
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.shortcuts import redirect, reverse
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from dictionary.utils.admin import log_admin


class ClearCache(PermissionRequiredMixin, TemplateView):
    template_name = "admin/sites/clear_cache.html"
    permission_required = "dictionary.can_clear_cache"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        context["title"] = _("Clear cache")
        return context

    def post(self, request, *args, **kwargs):
        if (key := request.POST.get("cache_key") or None) is not None:
            message = _("The cache with key '%(key)s' has been invalidated.") % {"key": key}
            cache.delete(key)
        else:
            message = _("All of cache has been invalidated.")
            cache.clear()

        log_admin(f"Cleared cache. /cache_key: {key}/", request.user, Site, request.site)
        notifications.warning(request, message)
        return redirect(reverse("admin:index"))
