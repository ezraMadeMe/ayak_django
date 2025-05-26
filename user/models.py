import hashlib
import random
import string
from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import UniqueConstraint


class BaseModel(models.Model):
    """공통 필드를 포함하는 추상 모델"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        abstract = True


class CodeGeneratorMixin:
    """코드 생성을 위한 믹스인"""

    @staticmethod
    def generate_unique_code(model_class, field_name, length=8, max_attempts=10):
        """고유한 코드 생성"""
        characters = string.ascii_uppercase + string.digits

        for _ in range(max_attempts):
            code = ''.join(random.choices(characters, k=length))
            if not model_class.objects.filter(**{field_name: code}).exists():
                return code

        raise ValidationError(f"고유한 {field_name} 생성에 실패했습니다.")


class User(BaseModel):
    """사용자 모델"""

    class Meta:
        db_table = 'users'
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

    def __str__(self):
        return f"{self.user_name} ({self.user_id})"


class Hospital(BaseModel, CodeGeneratorMixin):
    """병원 정보 모델"""

    class Meta:
        db_table = 'hospitals'
        verbose_name = '병원'
        verbose_name_plural = '병원들'
        constraints = [
            UniqueConstraint(
                fields=['user', 'hosp_code'],
                name='unique_user_hospital'
            )
        ]

    hospital_id = models.CharField(
        primary_key=True,
        max_length=8,
        editable=False,
        verbose_name='병원 등록 코드'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='hospitals',
        verbose_name='사용자'
    )
    hosp_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='병원 코드'
    )
    hosp_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='병원명'
    )
    hosp_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='병원 종별'
    )
    doctor_name = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='담당의'
    )
    address = models.TextField(
        blank=True,
        verbose_name='병원 주소'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='전화번호'
    )

    def save(self, *args, **kwargs):
        if not self.hospital_id:
            self.hospital_id = self.generate_unique_code(
                Hospital, 'hospital_id'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hosp_name} - {self.doctor_name}"


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
        User,
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


class MainIngredient(BaseModel):
    """주성분 모델 - 건강보험심사평가원 약가마스터 데이터 기반"""

    class Meta:
        db_table = 'main_ingredients'
        verbose_name = '주성분'
        verbose_name_plural = '주성분들'
        indexes = [
            models.Index(fields=['original_code'], name='idx_main_ingr_orig_code'),
            models.Index(fields=['main_ingr_name_kr'], name='idx_main_ingr_name_kr'),
            models.Index(fields=['main_ingr_name_en'], name='idx_main_ingr_name_en'),
            models.Index(fields=['classification_code'], name='idx_main_ingr_class'),
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


class IngredientAlias(BaseModel):
    """성분 별명/동의어 모델"""

    class Meta:
        db_table = 'ingredient_aliases'
        verbose_name = '성분 별명'
        verbose_name_plural = '성분 별명들'
        unique_together = [['ingredient', 'alias_name']]

    ingredient = models.ForeignKey(
        MainIngredient,
        on_delete=models.CASCADE,
        related_name='aliases',
        verbose_name='주성분'
    )

    alias_name = models.CharField(
        max_length=200,
        verbose_name='별명/동의어'
    )

    alias_type = models.CharField(
        max_length=20,
        choices=[
            ('TRADE', '상품명'),
            ('GENERIC', '일반명'),
            ('CHEMICAL', '화학명'),
            ('ABBREVIATION', '약어'),
            ('OTHER', '기타'),
        ],
        default='OTHER',
        verbose_name='별명 유형'
    )

    is_primary = models.BooleanField(
        default=False,
        verbose_name='주 별명 여부'
    )

    def __str__(self):
        return f"{self.ingredient.display_name} → {self.alias_name}"


class IngredientClassification(BaseModel):
    """성분 분류 모델"""

    class Meta:
        db_table = 'ingredient_classifications'
        verbose_name = '성분 분류'
        verbose_name_plural = '성분 분류들'

    code = models.IntegerField(
        primary_key=True,
        verbose_name='분류 코드'
    )

    name = models.CharField(
        max_length=100,
        verbose_name='분류명'
    )

    parent_code = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='상위 분류'
    )

    description = models.TextField(
        blank=True,
        verbose_name='설명'
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    def get_ingredients(self):
        """해당 분류의 모든 성분 조회"""
        return MainIngredient.objects.filter(
            classification_code=self.code,
            is_active=True
        )


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


class UserMedicalInfo(BaseModel):
    """사용자 의료 정보 (병원+질병 연결)"""

    class Meta:
        db_table = 'user_medical_info'
        verbose_name = '사용자 의료정보'
        verbose_name_plural = '사용자 의료정보들'
        constraints = [
            UniqueConstraint(
                fields=['user', 'hospital', 'illness'],
                name='unique_user_medical_info'
            )
        ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='medical_info',
        verbose_name='사용자'
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        verbose_name='병원'
    )
    illness = models.ForeignKey(
        Illness,
        on_delete=models.CASCADE,
        verbose_name='질병/증상'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='주 치료 여부'
    )

    def __str__(self):
        return f"{self.user.user_name} - {self.hospital.hosp_name} - {self.illness.ill_name}"

