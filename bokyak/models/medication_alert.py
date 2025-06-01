from django.db import models

from bokyak.models.medication_detail import MedicationDetail
from common.models.base_model import BaseModel


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
        related_name='alerts',
        verbose_name='복약 상세'
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
        return f"{self.medication_detail.cycle.group.group_name} - {self.get_alert_type_display()} ({self.alert_time})"
