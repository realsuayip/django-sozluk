from django.contrib import admin
from django.contrib.flatpages.models import FlatPage
from django.urls import reverse_lazy
from django.views.generic.base import RedirectView

from ..models import (
    AccountTerminationQueue,
    Badge,
    Conversation,
    ExternalURL,
    Memento,
    Message,
    MetaFlatPage,
    TopicFollowing,
    UserVerification,
)
from .author import AuthorAdmin
from .category import CategoryAdmin
from .entry import EntryAdmin
from .flatpages import FlatPageAdmin
from .general_report import GeneralReportAdmin
from .topic import TopicAdmin


admin.site.index_template = "dictionary/admin/index.html"
admin.site.login = RedirectView.as_view(url=reverse_lazy("login"))
admin.site.logout = RedirectView.as_view(url=reverse_lazy("logout"))

admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register(TopicFollowing)
admin.site.register(Memento)
admin.site.register(UserVerification)
admin.site.register(AccountTerminationQueue)
admin.site.register(Badge)

admin.site.unregister(FlatPage)
admin.site.register(MetaFlatPage, FlatPageAdmin)
admin.site.register(ExternalURL)
