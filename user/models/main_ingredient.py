import hashlib
from decimal import Decimal
from django.db import models
from common.models.base_model import BaseModel

class MainIngredient(BaseModel):
    """주성분 모델 - 건강보험심사평가원 약가마스터 데이터 기반"""

    class Meta:
        db_table = 'main_ingredients'
        verbose_name = '주성분'
        verbose_name_plural = '주성분들'
        ordering = ['-data_quality_score', 'main_ingr_name_kr', 'main_ingr_name_en']
        indexes = [
            models.Index(fields=['original_code'], name='idx_main_ingr_orig_code'),
            models.Index(fields=['main_ingr_name_kr'], name='idx_main_ingr_name_kr'),
            models.Index(fields=['main_ingr_name_en'], name='idx_main_ingr_name_en'),
            models.Index(fields=['classification_code'], name='idx_main_ingr_class'),
            models.Index(fields=['combination_group'], name='idx_main_ingr_combo'),
            models.Index(fields=['is_combination', 'is_active'], name='idx_main_ingr_status'),
        ]

    # 기본 식별자 (고유 키로 생성됨)
    ingr_code = models.CharField(
        primary_key=True,
        max_length=20,
        verbose_name='성분 고유 코드',
        help_text='원본 일반명코드 + 해시로 생성된 고유 식별자'
    )
    # 원본 데이터 필드들
    original_code = models.CharField(
        max_length=12,
        db_index=True,
        verbose_name='원본 일반명코드',
        help_text='건강보험심사평가원 원본 일반명코드'
    )
    dosage_form_code = models.CharField(
        max_length=3,
        blank=True,
        verbose_name='제형구분코드',
        help_text='TB, CH, LQ, PD 등'
    )
    dosage_form = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='제형',
        help_text='정제, 캡슐제, 액제, 산제 등'
    )
    # 성분명 (한글/영문)
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
    # 분류 및 투여경로
    classification_code = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='분류번호',
        help_text='약물 분류 번호'
    )
    administration_route = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='투여경로',
        help_text='내복, 외용, 주사 등'
    )
    # 함량 정보
    main_ingr_density = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal('0'),
        verbose_name='주성분 함량'
    )
    main_ingr_unit = models.CharField(
        max_length=20,
        default='mg',
        verbose_name='함량 단위',
        help_text='mg, g, ml, % 등'
    )
    # 원본 함량 표기 (파싱 전 원본)
    original_density_text = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='원본 함량 표기',
        help_text='1.1g(55mg/mL), 2mg/정(A정 14정중) 등 원본 표기'
    )
    # 복합제 정보
    is_combination = models.BooleanField(
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
    # 추가 메타데이터
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='비고'
    )
    # 데이터 품질 관련
    data_quality_score = models.IntegerField(
        default=0,
        verbose_name='데이터 품질 점수',
        help_text='0-100, 한글명/영문명/함량 완성도 기준'
    )

    def save(self, *args, **kwargs):
        """저장시 자동 처리"""
        # 복합제 그룹 설정
        if not self.combination_group:
            self.combination_group = self.original_code

        # 복합제 여부 자동 판단
        if not hasattr(self, '_skip_combination_check'):
            same_code_count = MainIngredient.objects.filter(
                original_code=self.original_code
            ).exclude(ingr_code=self.ingr_code).count()
            self.is_combination = same_code_count > 0

        # 데이터 품질 점수 계산
        if not hasattr(self, '_skip_quality_calc'):
            self.data_quality_score = self.calculate_data_quality()

        super().save(*args, **kwargs)

    def calculate_data_quality(self):
        """데이터 품질 점수 계산 (0-100)"""
        score = 0

        # 한글명 존재 (30점)
        if self.main_ingr_name_kr:
            score += 30

        # 영문명 존재 (20점)
        if self.main_ingr_name_en:
            score += 20

        # 함량 정보 존재 (25점)
        if self.main_ingr_density > 0:
            score += 25

        # 단위 정보 존재 (10점)
        if self.main_ingr_unit and self.main_ingr_unit != 'mg':
            score += 10

        # 제형 정보 존재 (10점)
        if self.dosage_form:
            score += 10

        # 분류 정보 존재 (5점)
        if self.classification_code:
            score += 5

        return min(score, 100)

    @property
    def display_name(self):
        """표시용 성분명"""
        if self.main_ingr_name_kr:
            return self.main_ingr_name_kr
        elif self.main_ingr_name_en:
            return self.main_ingr_name_en
        else:
            return f"성분_{self.original_code}"

    @property
    def full_density_info(self):
        """완전한 함량 정보"""
        if self.main_ingr_density > 0:
            return f"{self.main_ingr_density}{self.main_ingr_unit}"
        elif self.original_density_text:
            return self.original_density_text
        else:
            return "함량 정보 없음"

    @classmethod
    def generate_unique_code(cls, original_code, ingredient_name_kr='', ingredient_name_en=''):
        """고유 코드 생성"""
        # 성분 정보로 해시 생성
        ingredient_info = f"{original_code}_{ingredient_name_kr}_{ingredient_name_en}"
        hash_part = hashlib.md5(ingredient_info.encode('utf-8')).hexdigest()[:8]
        return f"{original_code}_{hash_part}"

    @classmethod
    def get_combination_ingredients(cls, original_code):
        """복합제의 모든 성분 조회"""
        return cls.objects.filter(
            original_code=original_code,
            is_active=True
        ).order_by('main_ingr_name_kr', 'main_ingr_name_en')

    @classmethod
    def search_by_name(cls, name):
        """성분명으로 검색"""
        return cls.objects.filter(
            models.Q(main_ingr_name_kr__icontains=name) |
            models.Q(main_ingr_name_en__icontains=name),
            is_active=True
        ).order_by('-data_quality_score')

    def get_related_combinations(self):
        """관련 복합제 조회"""
        if not self.is_combination:
            return MainIngredient.objects.none()

        return MainIngredient.objects.filter(
            combination_group=self.combination_group,
            is_active=True
        ).exclude(ingr_code=self.ingr_code)

    def __str__(self):
        combination_mark = " (복합제)" if self.is_combination else ""
        return f"{self.display_name} ({self.full_density_info}){combination_mark}"
