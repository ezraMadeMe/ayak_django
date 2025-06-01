from django.db import models
from django.utils import timezone

from common.models.base_model import BaseModel

class AyakUser(BaseModel):
    """사용자 모델"""

    class Meta:
        db_table = 'ayak_users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자들'

    user_id = models.CharField(
        primary_key=True,
        max_length=50,
        verbose_name='사용자 ID'
    )
    user_name = models.CharField(
        max_length=20,
        verbose_name='사용자 이름'
    )
    join_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='가입일'
    )
    push_agree = models.BooleanField(
        default=False,
        verbose_name='푸시 동의 여부'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
    )

    # def __str__(self):
    #     return f"{self.user_id}"
