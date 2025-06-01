from cmath import e

from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'
    verbose_name = '사용자 관리'

    def ready(self):
        try:
            import user.signals  # 시그널 등록
        except ImportError:
            print(f"Warning: Could not import user.signals - {e}")
