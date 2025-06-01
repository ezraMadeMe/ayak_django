from django.db import models
from django.db.models import UniqueConstraint

from bokyak.models.medication_cycle import MedicationCycle
from bokyak.models.prescription_medication import PrescriptionMedication
from common.models.base_model import BaseModel


# MedicationDetail 간소화
class MedicationDetail(BaseModel):
    """복약 상세 - 주기별 변화하는 정보만"""
    class Meta:
        db_table = 'medication_details'
        verbose_name = '복약 상세'
        verbose_name_plural = '복약 상세들'
        constraints = [
            UniqueConstraint(
                fields=['cycle', 'prescription_medication'],
                name='unique_cycle_medication'
            )
        ]

    cycle = models.ForeignKey(
        MedicationCycle,
        on_delete=models.CASCADE,
        related_name='medication_details',
        verbose_name='복약 주기'
    )
    prescription_medication = models.ForeignKey(
        PrescriptionMedication,
        on_delete=models.CASCADE,
        related_name='group_prescription',
        verbose_name='처방전 내 세부복약'
    )
    # 주기별 변화 정보만
    actual_dosage_pattern = models.JSONField(
        blank=True,
        null=True,
        help_text="템플릿과 다른 경우에만 저장"
    )
    remaining_quantity = models.PositiveIntegerField(
        verbose_name='잔여량'
    )
    # 환자 개별 조정사항
    patient_adjustments = models.JSONField(
        default=dict,
        help_text="환자별 용량 조정, 복용 시간 변경 등"
    )

    @property
    def effective_dosage_pattern(self):
        """실제 적용되는 복약 패턴"""
        return self.actual_dosage_pattern or self.prescription_medication.standard_dosage_pattern

    # @property
    # def medication(self):
    #     """역호환성을 위한 속성"""
    #     return self.medication_template.medication

    def save(self, *args, **kwargs):
        # if not self.remaining_quantity:
        #     self.remaining_quantity = self.cycle.prescription.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cycle.group.medical_info.user.user_name} - {self.cycle.group.group_name} - {self.cycle.group.prescription.prescription_date} - {self.prescription_medication.medication.item_name} 잔여량 {self.remaining_quantity}정"


