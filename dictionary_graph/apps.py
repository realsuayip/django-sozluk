from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DictionaryApiConfig(AppConfig):
    name = "dictionary_graph"
    verbose_name = _("Dictionary API")
