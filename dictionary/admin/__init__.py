from ..models import *
from django.contrib import admin

from .author import AuthorAdmin
from .category import CategoryAdmin
from .general_report import GeneralReportAdmin

admin.site.index_template = "dictionary/admin/index.html"
admin.site.register(Author, AuthorAdmin)
admin.site.register(Topic)
admin.site.register(Entry)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Message)
admin.site.register(Conversation)
admin.site.register(TopicFollowing)
admin.site.register(Memento)
admin.site.register(UserVerification)
admin.site.register(GeneralReport, GeneralReportAdmin)
