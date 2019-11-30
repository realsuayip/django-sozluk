from django.apps import AppConfig


class DictionaryConfig(AppConfig):
    name = 'dictionary'

    def ready(self):
        import dictionary.models.signals.messaging
