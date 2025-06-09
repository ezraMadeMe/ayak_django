import hashlib
from decimal import Decimal
from django.db import models
from common.models.base_model import BaseModel
#from user.models.medication import Medication


class MainIngredient(BaseModel):
    """주성분 모델 - 건강보험심사평가원 약가마스터 데이터 기반"""

    class Meta:
        db_table = 'main_ingredients'
        verbose_name = '주성분'
        verbose_name_plural = '주성분들'
        ordering = ['main_ingr_name_kr', 'main_ingr_name_en']
        indexes = [
            models.Index(fields=['main_ingr_name_kr'], name='idx_main_ingr_name_kr'),
            models.Index(fields=['main_ingr_name_en'], name='idx_main_ingr_name_en'),
            models.Index(fields=['combination_group'], name='idx_main_ingr_combo'),
        ]

    # 기본 식별자 (고유 키로 생성됨)
    ingr_code = models.CharField(
        primary_key=True,
        max_length=20,
        verbose_name='성분 고유 코드',
        help_text='일반명코드'
    )
    atc_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='ATC 코드',
        help_text='ATC 코드'
    )
    main_ingr_name_kr = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        verbose_name='주성분명(한글)'
    )
    main_ingr_name_en = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        verbose_name='주성분명(영문)'
    )
    # 함량 정보
    density = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('0'),
        verbose_name='주성분 함량'
    )
    unit = models.CharField(
        max_length=20,
        default='mg',
        verbose_name='함량 단위',
        help_text='mg, g, ml, % 등'
    )
    # 복합제 정보
    is_combination_drug = models.BooleanField(
        default=False,
        verbose_name='복합제 여부',
        help_text='하나의 일반명코드에 여러 성분이 포함된 경우'
    )
    combination_group = models.CharField(
        max_length=12,
        blank=True,
        db_index=True,
        verbose_name='복합제 그룹',
        help_text='같은 복합제에 속한 성분들의 그룹 식별자'
    )


    def save(self, *args, **kwargs):
        """저장시 자동 처리"""
        # 복합제 그룹 설정

        # 복합제 여부 자동 판단

        super().save(*args, **kwargs)

    @classmethod
    def get_combination_ingredients(cls, original_code):
        """복합제의 모든 성분 조회"""
        return cls.objects.filter(
            combination_group=original_code,
            is_active=True
        ).order_by('main_ingr_name_kr', 'main_ingr_name_en')

    def __str__(self):
        combination_mark = " (복합제)" if self.is_combination_drug else ""
        return f"{self.ingr_code} ({self.main_ingr_name_en}){combination_mark}"
