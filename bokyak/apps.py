from django.apps import AppConfig


class BokyakConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bokyak'
    verbose_name = '복약 관리'

    def ready(self):
        try:
            import bokyak.signals
        except ImportError as e:
            print(f"Warning: Could not import bokyak.signals - {e}")
