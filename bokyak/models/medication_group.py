from django.db import models

from common.models.base_model import BaseModel, CodeGeneratorMixin

class MedicationGroup(BaseModel, CodeGeneratorMixin):
    """복약그룹 모델 - 사용자가 설정하는 복약 단위"""

    class Meta:
        db_table = 'medication_groups'
        verbose_name = '복약그룹'
        verbose_name_plural = '복약그룹들'

    medical_info = models.ForeignKey(
        'user.UserMedicalInfo',
        on_delete=models.CASCADE,
        related_name='group_medical_info',
        verbose_name='의료 정보'
    )
    group_id = models.CharField(
        primary_key=True,
        max_length=10,
        editable=False,
        verbose_name='복약그룹 코드'
    )
    group_name = models.CharField(
        max_length=50,
        verbose_name='복약그룹명',
        help_text='예: 아침약, 바르는약, 혈압약 등'
    )
    # 사용자 설정
    reminder_enabled = models.BooleanField(
        default=True,
        verbose_name='알림 설정'
    )

    def save(self, *args, **kwargs):
        if not self.group_id:
            self.group_id = self.generate_unique_code(
                MedicationGroup, 'group_id', length=10
            )
        super().save(*args, **kwargs)

    def get_medications(self):
        """복약그룹에 포함된 의약품들 조회"""
        return self.group_medications.select_related('prescribed_medication__medication')

    def is_same_prescription_source(self, other_group):
        """다른 복약그룹과 같은 처방전을 공유하는지 확인"""
        return (self.medical_info.name == other_group.user and
                self.medical_info.name == other_group.user and
                self.medical_info.name == other_group.user)

    def __str__(self):
        return f"{self.group_name} - {self.medical_info.prescription_id}"
