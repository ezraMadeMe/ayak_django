from django.db import models

from common.models.base_model import BaseModel
from user.models.main_ingredient import MainIngredient


# 기존 Medication 모델과의 연결을 위한 개선된 중간 모델
class MedicationIngredient(BaseModel):
    """의약품-주성분 연결 모델 (개선된 버전)"""

    class Meta:
        db_table = 'medication_ingredients'
        verbose_name = '의약품 주성분'
        verbose_name_plural = '의약품 주성분들'
        unique_together = [['medication', 'ingredient']]
        indexes = [
            models.Index(fields=['medication'], name='idx_med_ingr_med'),
            models.Index(fields=['ingredient'], name='idx_med_ingr_ingr'),
        ]

    medication = models.ForeignKey(
        'Medication',  # 기존 Medication 모델 참조
        on_delete=models.CASCADE,
        related_name='ingredient_details',
        verbose_name='의약품'
    )

    ingredient = models.ForeignKey(
        MainIngredient,
        on_delete=models.CASCADE,
        related_name='medication_uses',
        verbose_name='주성분'
    )

    # 해당 의약품에서의 함량 정보 (원본 데이터와 다를 수 있음)
    content_amount = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        verbose_name='함량'
    )

    content_unit = models.CharField(
        max_length=20,
        verbose_name='함량 단위'
    )

    is_active_ingredient = models.BooleanField(
        default=True,
        verbose_name='주성분 여부',
        help_text='False인 경우 부형제나 첨가제'
    )

    def __str__(self):
        return f"{self.medication.item_name} - {self.ingredient.display_name} ({self.content_amount}{self.content_unit})"
