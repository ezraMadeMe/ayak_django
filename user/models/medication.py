from django.db import models

from common.models.base_model import BaseModel
from user.models.main_ingredient import MainIngredient


#from user.models.main_ingredient import MainIngredient


class Medication(BaseModel):
    """의약품 모델"""

    class Meta:
        db_table = 'medications'
        verbose_name = '의약품'
        verbose_name_plural = '의약품들'

    item_seq = models.BigIntegerField(
        primary_key=True,
        verbose_name='의약품 코드'
    )
    item_name = models.CharField(
        max_length=200,
        verbose_name='의약품명'
    )
    main_ingredients = models.ManyToManyField(
        MainIngredient,
        through='MedicationIngredient',
        verbose_name='주성분들'
    )
    entp_name = models.CharField(
        max_length=100,
        verbose_name='제조업체명'
    )
    item_image = models.ImageField(
        upload_to='medications/',
        blank=True,
        null=True,
        verbose_name='의약품 이미지'
    )
    class_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='약물 분류'
    )
    dosage_form = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='제형'
    )
    is_prescription = models.BooleanField(
        default=True,
        verbose_name='전문의약품 여부'
    )

    def __str__(self):
        return f"{self.item_name} ({self.entp_name})"
