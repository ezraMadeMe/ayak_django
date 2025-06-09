from django.db import models
from django.db.models import UniqueConstraint

from bokyak.models.medication_group import MedicationGroup
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
                fields=['group', 'prescription_medication'],
                name='unique_group_medication'
            )
        ]
    group = models.ForeignKey(
        MedicationGroup,
        on_delete=models.PROTECT,
        related_name='medication_details',
        help_text='복약 그룹'
    )
    prescription_medication = models.ForeignKey(
        PrescriptionMedication,
        on_delete=models.PROTECT,
        related_name='medication_details',
        help_text='처방약'
    )
    # 주기별 변화 정보만
    actual_dosage_pattern = models.JSONField(
        null=True,
        blank=True,
        help_text='환자 실제 복용 패턴',
    )
    actual_start_date = models.DateField(
        null=True,
        blank=True,
        help_text='실제 복용 시작일'
    )
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        help_text='실제 복용 종료일'
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
        return self.actual_dosage_pattern or self.prescription_medication


    def save(self, *args, **kwargs):
        # if not self.remaining_quantity:
        #     self.remaining_quantity = self.cycle.prescription.
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.prescription_medication.prescription_id}"


