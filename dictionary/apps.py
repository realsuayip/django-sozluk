from django.apps import AppConfig


# pylint: disable=C0415,W0611
class DictionaryConfig(AppConfig):
    name = 'dictionary'
    verbose_name = "Sözlük"

    def ready(self):
        import dictionary.signals.messaging
