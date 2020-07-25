from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


class DictionaryApiConfig(AppConfig):
    name = "dictionary_graph"
    verbose_name = _lazy("Dictionary API")
