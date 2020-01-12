from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib import messages as notifications
from django.contrib import admin
from django.db.models import Count
from django.shortcuts import redirect, reverse, render
from django.utils.functional import cached_property
from django.views.generic import View

from ...models import Author, Entry, Topic, Message
from ...utils import parse_date_or_none, log_admin
from ...utils.settings import GENERIC_SUPERUSER_ID


class InputNotInDesiredRangeError(Exception):
    pass


class TopicMove(PermissionRequiredMixin, View):
    permission_required = ('dictionary.move_topic', 'dictionary.change_topic')

    def get(self, request):
        try:
            context = self.get_context_data()
        except Topic.DoesNotExist:
            notifications.error(request, "Kaynak başlık(lar) bulunamadı.")
            return redirect(reverse("admin:dictionary_topic_changelist"))

        return render(request, "dictionary/admin/actions/topic_move.html", context)

    def post(self, request):
        add_bkz = request.POST.get("add_bkz") == "yes"
        target_topic = request.POST.get("target_topic", "").strip()
        from_date = parse_date_or_none(request.POST.get("from_date"))
        to_date = parse_date_or_none(request.POST.get("to_date"))

        try:
            target_object = Topic.objects.get(title=target_topic)
            generic_superuser = Author.objects.get(pk=GENERIC_SUPERUSER_ID)

            entries_list = Entry.objects_published.filter(topic__in=self.source_objects)

            if from_date:
                entries_list = entries_list.filter(date_created__gte=from_date)

            if to_date:
                entries_list = entries_list.filter(date_created__lte=to_date)

            entries_count = entries_list.count()

            # Inform user that their entries have been moved to another topic
            for entry in entries_list:
                msg = f"`{entry.topic.title}` başlığındaki " \
                      f"`#{entry.pk}` numaralı entry'niz `{target_object.title}` başlığına taşındı"
                Message.objects.compose(generic_superuser, entry.author, msg)

            entries_list.update(topic=target_object)  # Actual movement happens here

            # Include an informative entry on old topic to indicate the new topic
            if add_bkz:
                bulk_list = [Entry(topic=obj, content=f"(bkz: {target_object.title})", author=generic_superuser) for obj
                             in self.source_objects]
                Entry.objects.bulk_create(bulk_list)

            log_admin(f"bu başlığa {entries_count} entry(ler) taşındı. sources->{self.source_objects},"
                      f"from->{from_date} to->{to_date}", request.user, Topic, target_object)
            notifications.success(request, f"{entries_count} tane entry güncellendi.")
        except Topic.DoesNotExist:
            notifications.error(request, "Hedef başlık bulunamadı.")
        except Author.DoesNotExist:
            notifications.error(request, "GENERIC_SUPERUSER bulunamadı?")

        return redirect(reverse("admin:dictionary_topic_changelist"))

    def get_context_data(self):
        admin_context = admin.site.each_context(self.request)
        meta = {"title": "Başlık taşıma"}
        source = {"sources": self.source_objects}
        context = {**admin_context, **source, **meta}
        return context

    @cached_property
    def source_objects(self):
        max_input = 500  # SQLITE will raise OperationalError > 999, (check your database backend before exceeding 500)

        # Get which objects are selected to perform the acion
        try:
            source_list = self.request.GET.get("source_list", "")
            source_ids = [int(pk) for pk in source_list.split("-")]
            if len(source_ids) > max_input:
                raise InputNotInDesiredRangeError

            objects = Topic.objects.annotate(entry_count=Count("entries")).filter(pk__in=source_ids, entry_count__gt=0)
        except (ValueError, OverflowError):
            objects = None
        except InputNotInDesiredRangeError:
            objects = None
            notifications.error(self.request, f"Bir anda en çok {max_input} başlık taşınabilir.")

        if not objects:
            raise Topic.DoesNotExist

        return list(objects)
