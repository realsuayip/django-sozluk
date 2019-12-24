from django.apps import AppConfig


class DictionaryConfig(AppConfig):
    name = 'dictionary'
    verbose_name = "Sözlük"

    def ready(self):
        import dictionary.signals.messaging
