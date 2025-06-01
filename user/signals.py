
# user/signals.py 파일 생성 (없는 경우)
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from .models.ayakuser import AyakUser

@receiver(post_save, sender=AyakUser)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """사용자 생성 시 토큰 자동 생성"""
    # if created:
        # Token.objects.create(user=instance)

@receiver(post_save, sender=AyakUser)
def save_user_profile(sender, instance, **kwargs):
    """사용자 저장 시 추가 로직"""
    # 여기에 사용자 관련 추가 로직을 작성
    pass
