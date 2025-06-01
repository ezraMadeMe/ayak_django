from django.db import models
from django.db.models import UniqueConstraint

from common.models.base_model import BaseModel, CodeGeneratorMixin
from user.models.ayakuser import AyakUser


class Illness(BaseModel, CodeGeneratorMixin):
    """질병/증상 모델"""

    class IllnessType(models.TextChoices):
        DISEASE = 'DISEASE', '질병'
        SYMPTOM = 'SYMPTOM', '증상'

    class Meta:
        db_table = 'illnesses'
        verbose_name = '질병/증상'
        verbose_name_plural = '질병/증상들'
        constraints = [
            UniqueConstraint(
                fields=['user', 'ill_name', 'ill_type'],
                name='unique_user_illness'
            )
        ]

    illness_id = models.CharField(
        primary_key=True,
        max_length=8,
        editable=False,
        verbose_name='질병/증상 코드'
    )
    user = models.ForeignKey(
        AyakUser,
        on_delete=models.CASCADE,
        related_name='illnesses',
        verbose_name='사용자'
    )
    ill_type = models.CharField(
        max_length=10,
        choices=IllnessType.choices,
        default=IllnessType.DISEASE,
        verbose_name='구분'
    )
    ill_name = models.CharField(
        max_length=100,
        verbose_name='질병/증상명'
    )
    ill_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='질병 코드 (ICD-10 등)'
    )
    ill_start = models.DateField(
        blank=True,
        null=True,
        verbose_name='발병일/발생일'
    )
    ill_end = models.DateField(
        blank=True,
        null=True,
        verbose_name='완치일'
    )
    is_chronic = models.BooleanField(
        default=False,
        verbose_name='만성 질환 여부'
    )

    def save(self, *args, **kwargs):
        if not self.illness_id:
            self.illness_id = self.generate_unique_code(
                Illness, 'illness_id'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ill_name} ({self.get_ill_type_display()})"
