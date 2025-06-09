from django.db import models
from common.models.base_model import BaseModel
from user.models.main_ingredient import MainIngredient


class Medication(BaseModel):
    """의약품 모델"""

    class Meta:
        db_table = 'medications'
        verbose_name = '의약품'
        verbose_name_plural = '의약품들'

    medication_id = models.BigIntegerField(
        primary_key=True,
        verbose_name='의약품 코드'
    )
    medication_name = models.CharField(
        max_length=200,
        verbose_name='의약품명'
    )
    main_item_ingr = models.CharField(
        max_length=100,
        null=True,
        help_text='국문 주성분'
    )
    main_ingr_eng = models.CharField(
        max_length=100,
        null=True,
        help_text='영문 주성분'
    )
    ingredients = models.ManyToManyField(
        MainIngredient,
        through='MedicationIngredient',
        related_name='related_medications',
        blank=True,
        verbose_name='주성분들'
    )
    manufacturer = models.CharField(
        max_length=100, 
        help_text='제조사'
    )
    item_image = models.ImageField(
        upload_to='medications/',
        blank=True,
        null=True,
        verbose_name='의약품 이미지'
    )

    def __str__(self):
        return f'{self.medication_name} ({self.manufacturer})'

    def get_main_ingredients(self):
        """주성분 목록 반환"""
        return self.ingredients.filter(is_active=True)

    def get_ingredient_summary(self):
        """성분 요약 정보"""
        main_ingredients = self.get_main_ingredients()
        if main_ingredients.exists():
            ingredient_list = []
            for mi in main_ingredients:
                ingredient_list.append(f"{mi.main_ingredient.main_ingr_name_kr} {mi.content_display}")
            return ", ".join(ingredient_list)
        return "성분 정보 없음"

    def is_combination_drug(self):
        """복합제 여부 판정"""
        return self.get_main_ingredients().count() > 1