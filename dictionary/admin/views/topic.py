from django.contrib import messages as notifications
from django.db.models import Count
from django.shortcuts import redirect

from ...models import Author, Entry, Topic, Message
from ...utils import parse_date_or_none, log_admin, get_generic_superuser
from ...utils.views import IntermediateActionView


class TopicMove(IntermediateActionView):
    """
    Move entries in selected range of (a) topic(s) to another topic. Send a informative message to users for each entry
    they have in that topic. If wanted, include a reference for new topic in the old topic(s). An admin log is created
    for this action.
    """
    max_input = 15
    permission_required = ('dictionary.move_topic', 'dictionary.change_topic')
    model = Topic
    template_name = "dictionary/admin/actions/topic_move.html"
    page_title = "Başlık taşıma"

    def get_queryset(self):
        queryset = self.model.objects.annotate(entry_count=Count("entries")).filter(pk__in=self.get_source_ids(),
                                                                                    entry_count__gt=0)
        return queryset

    def post(self, request):
        add_bkz = request.POST.get("add_bkz") == "yes"
        target_topic = request.POST.get("target_topic", "").strip()
        from_date = parse_date_or_none(request.POST.get("from_date"))
        to_date = parse_date_or_none(request.POST.get("to_date"))

        try:
            target_object = Topic.objects.get(title=target_topic)
            generic_superuser = get_generic_superuser()

            topic_list_raw = list(self.object_list)
            entries_list = Entry.objects_published.filter(topic__in=topic_list_raw)

            if from_date:
                entries_list = entries_list.filter(date_created__gte=from_date)

            if to_date:
                entries_list = entries_list.filter(date_created__lte=to_date)

            entries_list_raw = list(entries_list)
            entries_count = len(entries_list_raw)

            for entry in entries_list_raw:
                # Inform user that their entries have been moved to another topic
                msg = f"`{entry.topic.title}` başlığındaki " \
                      f"`#{entry.pk}` numaralı entry'niz `{target_object.title}` başlığına taşındı"
                Message.objects.compose(generic_superuser, entry.author, msg)

                # Migrate entry
                entry.topic = target_object
                entry.save()

            # Include an informative entry on old topic to indicate the new topic
            if add_bkz:
                bulk_list = [Entry(topic=obj, content=f"(bkz: {target_object.title})", author=generic_superuser) for obj
                             in topic_list_raw]
                Entry.objects.bulk_create(bulk_list)

            # Admin log
            log_admin(f"bu başlığa {entries_count} entry(ler) taşındı. sources->{topic_list_raw},"
                      f"from->{from_date} to->{to_date}", request.user, Topic, target_object)

            notifications.success(request, f"{entries_count} tane entry güncellendi.")
        except Topic.DoesNotExist:
            notifications.error(request, "Hedef başlık bulunamadı.")
        except Author.DoesNotExist:
            notifications.error(request, "GENERIC_SUPERUSER bulunamadı?")

        return redirect(self.get_changelist_url())
