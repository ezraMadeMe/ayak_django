from bokyak.models import MedicationGroup
from bokyak.models.prescription import Prescription
from user.models import Medication
from user.models.user_medical_info import BaseModel
from django.db import models


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
    group = models.ForeignKey(
        MedicationGroup,
        on_delete=models.CASCADE,
        related_name='prescribed_group',
        verbose_name='관련 복약그룹'
    )
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='prescribed_medications',
        verbose_name='처방전'
    )
    medication = models.ForeignKey(
        Medication,
        on_delete=models.CASCADE,
        related_name='prescription_uses',
        verbose_name='의약품'
    )
    # 처방 정보
    standard_dosage_pattern = models.JSONField(
        default=list,
        verbose_name='복약 처방',
        help_text='["D", "A", "E", "N", "P"] - 아침/점심/저녁/취침전/필요시(["시간대":"복용량"] 리스트)'
    )
    duration_days = models.IntegerField(
        verbose_name='처방일수'
    )
    total_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='총 처방량(1회 용량*복약 빈도*복약 개수*복약 단위?)'
    )

    def __str__(self):
        return f"{self.medication.item_name} 총 {self.total_quantity}정 {self.duration_days}일"
