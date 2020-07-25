from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _lazy


# pylint: disable=C0415,W0611
class DictionaryConfig(AppConfig):
    name = "dictionary"
    verbose_name = _lazy("Dictionary")

    def ready(self):
        import dictionary.signals
