from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect, reverse


# Admin site specific utilities


def log_admin(msg, authorizer, model_type, model_object, flag=CHANGE):
    LogEntry.objects.log_action(user_id=authorizer.id, content_type_id=ContentType.objects.get_for_model(model_type).pk,
                                object_id=model_object.id, object_repr=str(model_object), change_message=msg,
                                action_flag=flag)


def logentry_instance(msg, authorizer, model_type, model_object, flag=CHANGE):
    return LogEntry(user_id=authorizer.pk, content_type=ContentType.objects.get_for_model(model_type),
                    object_id=model_object.pk, change_message=msg, action_flag=flag)


def logentry_bulk_create(*logentry_instances):
    LogEntry.objects.bulk_create(*logentry_instances)


class IntermediateActionHandler:
    def __init__(self, queryset, url_name):
        self.queryset = queryset
        self.url_name = url_name

    def get_source_list(self):
        return '-'.join([str(value["id"]) for value in self.queryset.values("id")])

    @property
    def redirect_url(self):
        return redirect(reverse(self.url_name) + f"?source_list={self.get_source_list()}")
