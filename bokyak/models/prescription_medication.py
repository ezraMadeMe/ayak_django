from django.db import models

from bokyak.models.medication_group import MedicationGroup
from user.models import Medication
from user.models.user_medical_info import BaseModel
from bokyak.models.prescription import Prescription


class PrescriptionMedication(BaseModel):
    """처방전 의약품 모델 (처방전에 포함된 실제 의약품들)"""

    class Meta:
        db_table = 'prescription_medications'
        verbose_name = '처방 의약품'
        verbose_name_plural = '처방 의약품들'
        unique_together = [['prescription', 'medication']]
        indexes = [
            models.Index(fields=['prescription'], name='idx_presc_med_prescription'),
            models.Index(fields=['medication'], name='idx_presc_med_medication'),
        ]
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='prescribed_medications',
        verbose_name='처방전'
    )
    medication = models.ForeignKey(
        'user.Medication',
        on_delete=models.CASCADE,
        related_name='prescribed_medications',
        verbose_name='의약품 정보'
    )
    group = models.ForeignKey(
        MedicationGroup,
        on_delete=models.CASCADE,
        related_name='prescribed_medications',
        verbose_name='관련 복약그룹'
    )
    # 처방 정보
    standard_dosage_pattern = models.JSONField(
        default=list,
        verbose_name='복약 패턴(복약 시간대 별 복용량)',
        help_text='["D", "A", "E", "N", "P"] - 아침/점심/저녁/취침전/필요시(["시간대":"복용량"] 리스트)'
    )
    patient_dosage_pattern = models.JSONField(
        null=True,
        help_text='환자 특수 복약 패턴(복약 시간대 별 복용량)'
    )
    duration_days = models.IntegerField(
        verbose_name='처방일수'
    )
    total_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='총 처방량'
    )
    source_prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_medications',
        help_text='원본 처방전'
    )

    def __str__(self):
        return f"{self.medication.medication_name} 총 {self.total_quantity}정 {self.duration_days}일"
