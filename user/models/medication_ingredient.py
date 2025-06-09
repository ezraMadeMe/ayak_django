from django.db import models
from common.models.base_model import BaseModel
from user.models.medication import Medication
from user.models.main_ingredient import MainIngredient


# 기존 Medication 모델과의 연결을 위한 개선된 중간 모델
class MedicationIngredient(BaseModel):
    """의약품-주성분 연결 모델 (개선된 버전)"""

    class Meta:
        db_table = 'medication_ingredients'
        verbose_name = '의약품 주성분'
        verbose_name_plural = '의약품 주성분들'
        unique_together = [['medication', 'main_ingredient']]
        indexes = [
            models.Index(fields=['medication'], name='idx_med_ingr_med'),
            models.Index(fields=['main_ingredient'], name='idx_med_ingr_ingr'),
        ]

    medication = models.ForeignKey(
        Medication,
        on_delete=models.CASCADE,
        related_name='medication_ingredients',
        help_text='약물'
    )
    main_ingredient = models.ForeignKey(
        MainIngredient,
        on_delete=models.PROTECT,
        related_name='medication_ingredients',
        help_text='성분'
    )
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text='함량'
    )
    unit = models.CharField(
        max_length=20, 
        help_text='단위'
    )
    is_main = models.BooleanField(
        default=True, 
        help_text='False인 경우 부형제나 첨가제'
    )
    # 추가 정보
    ingredient_role = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="성분역할"
    )  # 주성분, 부형제, 첨가제 등
    notes = models.TextField(
        blank=True,
        verbose_name="비고"
    )

    def __str__(self):
        return f'{self.medication.item_name} - {self.ingredient.ingredient_name}'
