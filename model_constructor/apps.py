from django.apps import AppConfig


class ModelConstructorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'model_constructor'

    def ready(self):
        import model_constructor.models
