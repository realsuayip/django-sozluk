from django.template.defaultfilters import linebreaksbr
from django.utils import timezone
from django.utils.translation import gettext as _


from graphene import ID, Mutation, String

from dictionary.models import Entry, Topic
from dictionary.templatetags.filters import formatted
from dictionary.utils.validators import validate_user_text

from dictionary_graph.utils import login_required


class DraftEdit(Mutation):
    pk = ID()
    content = String()
    feedback = String()

    class Arguments:
        content = String()
        pk = ID(required=False)
        title = String(required=False)

    @staticmethod
    @login_required
    def mutate(_root, info, content, pk=None, title=None):
        validate_user_text(content, exctype=ValueError)

        if pk:
            entry = Entry.objects_all.get(is_draft=True, author=info.context.user, pk=pk)
            entry.content = content
            entry.date_edited = timezone.now()
            entry.save(update_fields=["content", "date_edited"])
            return DraftEdit(
                pk=entry.pk,
                content=linebreaksbr(formatted(entry.content)),
                feedback=_("your changes have been saved as draft"),
            )

        if title:
            topic = Topic.objects.get_or_pseudo(unicode_string=title)

            if (topic.exists and topic.is_banned) or not topic.valid:
                raise ValueError(_("we couldn't handle your request. try again later."))

            if not topic.exists:
                topic = Topic.objects.create_topic(title=topic.title)

            entry = Entry(author=info.context.user, topic=topic, content=content, is_draft=True)
            entry.save()
            return DraftEdit(
                pk=entry.pk,
                content=linebreaksbr(formatted(entry.content)),
                feedback=_("your entry has been saved as draft"),
            )

        raise ValueError(_("we couldn't handle your request. try again later."))
