from django.contrib import messages as notifications
from django.shortcuts import redirect
from django.utils.translation import gettext, gettext_lazy as _, ngettext, pgettext

from dictionary.models import Author, Entry, Topic
from dictionary.utils import get_generic_superuser, parse_date_or_none
from dictionary.utils.admin import log_admin
from dictionary.utils.views import IntermediateActionView


class TopicMove(IntermediateActionView):
    """
    Move entries in (selected range of) (a) topic(s) to another topic. If wanted,
    include a reference for new topic in (the) old topic(s). An admin log
    -for target topic- is created for this action.
    """

    max_input = 15
    permission_required = ("dictionary.move_topic", "dictionary.change_topic")
    model = Topic
    template_name = "admin/actions/topic_move.html"
    page_title = _("Topic transfer")

    def get_queryset(self):
        return self.model.objects_published.filter(pk__in=self.get_source_ids())

    def post(self, request):
        reference = request.POST.get("reference") == "yes"
        target_topic = request.POST.get("target_topic", "").strip()
        from_date = parse_date_or_none(request.POST.get("from_date"))
        to_date = parse_date_or_none(request.POST.get("to_date"))

        try:
            target_topic = Topic.objects.get(title=target_topic)
            generic_superuser = get_generic_superuser()

            topic_list_raw = list(self.get_object_list())
            entries_list = Entry.objects_published.filter(topic__in=topic_list_raw)

            if from_date:
                entries_list = entries_list.filter(date_created__gte=from_date)

            if to_date:
                entries_list = entries_list.filter(date_created__lte=to_date)

            entries_count = entries_list.count()
            entries_list.update(topic=target_topic)  # Bulk update, does not call save()
            target_topic.register_wishes()

            # Include an informative entry on old topic to indicate the new topic
            if reference:
                bulk_list = [
                    Entry(
                        topic=obj,
                        content=f"({pgettext('editor', 'see')}: {target_topic.title})",
                        author=generic_superuser,
                    )
                    for obj in topic_list_raw
                ]
                Entry.objects.bulk_create(bulk_list)

            # Admin log
            log_admin(
                f"TopicMove action, count: {entries_count}. sources->{topic_list_raw},"
                f"from->{from_date} to->{to_date}",
                request.user,
                Topic,
                target_topic,
            )

            notifications.success(
                request,
                ngettext("%(count)d entry was transferred", "%(count)d entries were transferred", entries_count)
                % {"count": entries_count},
            )
        except Topic.DoesNotExist:
            notifications.error(request, gettext("Couldn't find the target topic."))
        except Author.DoesNotExist:
            notifications.error(request, gettext("GENERIC_SUPERUSER is missing?"))

        return redirect(self.get_changelist_url())
