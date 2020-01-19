from django.contrib import admin

from ..models import Conversation, Memento, Message, TopicFollowing, UserVerification
from .author import AuthorAdmin
from .category import CategoryAdmin
from .entry import EntryAdmin
from .general_report import GeneralReportAdmin
from .topic import TopicAdmin


admin.site.index_template = "dictionary/admin/index.html"
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register(TopicFollowing)
admin.site.register(Memento)
admin.site.register(UserVerification)
