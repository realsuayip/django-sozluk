from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType


# General utilities

def turkish_lower(turkish_string):
    lower_map = {ord(u'I'): u'ı', ord(u'İ'): u'i', }
    return turkish_string.translate(lower_map).lower()


def log_admin(msg, authorizer, model_type, model_object, flag=CHANGE):
    LogEntry.objects.log_action(user_id=authorizer.id, content_type_id=ContentType.objects.get_for_model(model_type).pk,
                                object_id=model_object.id, object_repr=f"{msg}", change_message=msg, action_flag=flag)
