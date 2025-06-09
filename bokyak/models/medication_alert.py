from django.db import models
from common.models.base_model import BaseModel
from bokyak.models.medication_detail import MedicationDetail


class MedicationAlert(BaseModel):
    """복약 알림 모델"""

    class AlertType(models.TextChoices):
        DOSAGE = 'DOSAGE', '복용 알림'
        REFILL = 'REFILL', '처방전 갱신 알림'
        APPOINTMENT = 'APPOINTMENT', '진료 예약 알림'

    class Meta:
        db_table = 'medication_alerts'
        verbose_name = '복약 알림'
        verbose_name_plural = '복약 알림들'

    medication_detail = models.ForeignKey(
        MedicationDetail,
        on_delete=models.CASCADE,
        related_name='medication_alerts',
        help_text='복약 상세'
    )
    alert_type = models.CharField(
        max_length=15,
        choices=AlertType.choices,
        verbose_name='알림 유형'
    )
    alert_time = models.TimeField(
        verbose_name='알림 시간'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='알림 활성화'
    )
    message = models.TextField(
        blank=True,
        verbose_name='알림 메시지'
    )

    def __str__(self):
        return f'{self.medication_detail} - {self.alert_time}'
