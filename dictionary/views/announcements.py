from django.utils import timezone
from django.views.generic.dates import ArchiveIndexView, DateDetailView, MonthArchiveView

from dictionary.models import Announcement


class AnnouncementMixin:
    model = Announcement
    date_field = "date_created"
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().select_related("discussion")


class AnnouncementIndex(AnnouncementMixin, ArchiveIndexView):
    template_name = "dictionary/announcements/index.html"
    allow_empty = True
    date_list_period = "month"

    def dispatch(self, request, *args, **kwargs):
        # Mark announcements read
        if request.user.is_authenticated and request.user.unread_topic_count["announcements"] > 0:
            request.user.announcement_read = timezone.now()
            request.user.save()
            self.request.user.invalidate_unread_topic_count()
            del request.user.unread_topic_count  # reset cached_property

        return super().dispatch(request, *args, **kwargs)


class AnnouncementMonth(AnnouncementMixin, MonthArchiveView):
    template_name = "dictionary/announcements/month.html"
    date_list_period = "month"
    context_object_name = "latest"

    def get_date_list(self, queryset, **kwargs):
        # To list ALL months in date_list (the archive doesn't go deeper at this point)
        return super().get_date_list(queryset=self.model.objects.all(), ordering="DESC", **kwargs)


class AnnouncementDetail(AnnouncementMixin, DateDetailView):
    template_name = "dictionary/announcements/detail.html"
    context_object_name = "post"
