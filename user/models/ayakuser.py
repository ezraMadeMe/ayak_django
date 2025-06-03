import uuid

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone

from common.models.base_model import BaseModel

class AyakUser(AbstractUser):
    """사용자 모델"""

    class Meta:
        db_table = 'ayak_users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'

    user_id = models.CharField(max_length=50, unique=True, primary_key=True)
    user_name = models.CharField(max_length=100)
    join_date = models.DateTimeField(auto_now_add=True)
    push_agree = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # 소셜 로그인 관련 필드
    social_provider = models.CharField(max_length=20, blank=True, null=True)  # 'google', 'kakao', 'apple' 등
    social_id = models.CharField(max_length=100, blank=True, null=True)  # 소셜 로그인 고유 ID
    email = models.EmailField(blank=True, null=True)
    profile_image_url = models.URLField(blank=True, null=True)

    # 추가 사용자 정보
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, blank=True, null=True)  # 'M', 'F', 'OTHER'

    # 앱 설정
    notification_enabled = models.BooleanField(default=True)
    marketing_agree = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_date = models.DateTimeField(blank=True, null=True)

    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text=(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name="ayakuser_set",  # 👈 여기에 고유한 related_name 추가
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="ayakuser_permissions_set",  # 👈 여기에 고유한 related_name 추가
        related_query_name="user",
    )

    # AbstractUser의 username 필드를 user_id로 대체
    USERNAME_FIELD = 'user_id'
    REQUIRED_FIELDS = ['user_name']

    class Meta:
        db_table = 'ayak_users'

    def save(self, *args, **kwargs):
        # user_id가 없으면 자동 생성
        if not self.user_id:
            self.user_id = self.generate_user_id()

        # username을 user_id와 동일하게 설정 (AbstractUser 호환)
        self.username = self.user_id

        super().save(*args, **kwargs)

    def generate_user_id(self):
        """고유한 사용자 ID 생성"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_suffix = str(uuid.uuid4().hex)[:6].upper()
        return f"AYAK_{timestamp}_{random_suffix}"
