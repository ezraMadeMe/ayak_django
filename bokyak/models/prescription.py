from django.db import models

from common.models.base_model import BaseModel, CodeGeneratorMixin


# 기존 모델에 추가할 새로운 모델들
class Prescription(BaseModel, CodeGeneratorMixin):
    """처방전 모델"""

    class Meta:
        db_table = 'prescriptions'
        verbose_name = '처방전'
        verbose_name_plural = '처방전들'
        indexes = [
            models.Index(fields=['prescription_date'], name='idx_prescription_date'),
            models.Index(fields=['is_active'], name='idx_prescription_active'),
        ]

    prescription_id = models.CharField(
        primary_key=True,
        max_length=12,
        editable=False,
        verbose_name='처방전 코드'
    )
    prescription_count = models.PositiveIntegerField(
        default=0,
        verbose_name='동일 처방전 갱신 횟수'
    )
    prescription_date = models.DateField(
        verbose_name='처방일/내원일'
    )
    previous_prescription = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_prescriptions',
        verbose_name='이전 처방전',
        help_text='갱신된 경우 이전 처방전 참조'
    )
    # 처방전 갱신 관리
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
    )

    def save(self, *args, **kwargs):
        if not self.prescription_id:
            self.prescription_id = self.generate_unique_code(
                Prescription, 'prescription_id', length=12
            )

        # 이전 처방전이 존재하는 경우 prescription_count 증가
        if self.previous_prescription is not None:
            self.prescription_count = self.previous_prescription.prescription_count + 1
        else:
            # 최초 처방전인 경우 0으로 설정
            self.prescription_count = 0
        super().save(*args, **kwargs)

    def update_prescription(self, new_prescription_data):
        """
        처방전 갱신 시 기존 처방전을 비활성화하고 새 처방전 생성
        연결된 복약그룹들도 자동으로 새 처방전으로 업데이트
        """
        # 기존 처방전 비활성화
        self.is_active = False
        self.save()

        # 새 처방전 생성
        new_prescription_data['previous_prescription'] = self

        new_prescription = Prescription.objects.create(**new_prescription_data)

        # 연결된 복약그룹들을 새 처방전으로 업데이트
        medication_groups = self.medication_groups.all()
        for group in medication_groups:
            group.prescription = new_prescription
            group.save()

        return new_prescription

    def __str__(self):
        return f"{self.prescription_date} - {self.prescription_id}"
