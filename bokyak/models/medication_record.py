from django.db import models

from bokyak.models.medication_detail import MedicationDetail
from common.models.base_model import BaseModel


class MedicationRecord(BaseModel):
    """복약 기록 모델"""

    class Meta:
        db_table = 'medication_records'
        verbose_name = '복약 기록'
        verbose_name_plural = '복약 기록들'
        ordering = ['-record_date']
        indexes = [
            models.Index(fields=['medication_detail', 'record_date'], name='idx_med_record_user_date'),
        ]

    class RecordType(models.TextChoices):
        TAKEN = 'TAKEN', '복용함'
        MISSED = 'MISSED', '복용 누락'
        SIDE_EFFECT = 'SIDE_EFFECT', '부작용'
        SKIPPED = 'SKIPPED', '의도적 건너뜀'
        NOTE = 'NOTE', '메모'


    def __str__(self):
        # status = "복용완료" if self.is_taken else ("건너뜀" if self.is_skipped else "미복용")
        return f"{self.medication_detail.name} - {self.record_date} ({self.record_date} {self.quantity_taken}) - {self.updated_at}"

    medication_detail = models.ForeignKey(
        MedicationDetail,
        on_delete=models.CASCADE,
        related_name='medication_records',
        help_text='복약 상세'
    )
    record_type = models.CharField(
        max_length=15,
        choices=RecordType.choices,
        default=RecordType.TAKEN,
        verbose_name='기록 유형'
    )
    record_date = models.DateTimeField(
        verbose_name='기록 일시'
    )
    quantity_taken = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='복용량'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='기록 내용'
    )
    effectiveness_score = models.IntegerField(
        null=True, 
        blank=True,
        verbose_name='효과 점수'
    )
    tags = models.JSONField(
        default=list,
        verbose_name='태그'
    )

    def __str__(self):
        return f'{self.medication_detail.prescription_medication.medication.item_name} - {self.record_date}'
