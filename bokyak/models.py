from django.db.models import UniqueConstraint

from user.models import BaseModel, CodeGeneratorMixin, UserMedicalInfo
from django.db import models

class MedicationGroup(BaseModel, CodeGeneratorMixin):
    """복약 그룹 모델"""

    class Meta:
        db_table = 'medication_groups'
        verbose_name = '복약 그룹'
        verbose_name_plural = '복약 그룹들'

    group_id = models.CharField(
        primary_key=True,
        max_length=8,
        editable=False,
        verbose_name='복약 그룹 코드'
    )
    medical_info = models.ForeignKey(
        'user.UserMedicalInfo',
        on_delete=models.CASCADE,
        related_name='medication_groups',
        verbose_name='의료 정보'
    )
    group_name = models.CharField(
        max_length=50,
        verbose_name='복약 그룹명'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
    )

    def save(self, *args, **kwargs):
        if not self.group_id:
            self.group_id = self.generate_unique_code(
                MedicationGroup, 'group_id'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group_name} ({self.medical_info.user.user_name})"


class MedicationCycle(BaseModel):
    """복약 사이클 모델"""

    class Meta:
        db_table = 'medication_cycles'
        verbose_name = '복약 사이클'
        verbose_name_plural = '복약 사이클들'
        constraints = [
            UniqueConstraint(
                fields=['group', 'cycle_number'],
                name='unique_group_cycle'
            )
        ]
        ordering = ['-cycle_start']

    group = models.ForeignKey(
        MedicationGroup,
        on_delete=models.CASCADE,
        related_name='cycles',
        verbose_name='복약 그룹'
    )
    cycle_number = models.PositiveIntegerField(
        verbose_name='사이클 번호'
    )
    cycle_start = models.DateField(
        verbose_name='사이클 시작일'
    )
    cycle_end = models.DateField(
        blank=True,
        null=True,
        verbose_name='사이클 종료일'
    )
    prescription_date = models.DateField(
        verbose_name='처방일'
    )
    next_visit_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='다음 방문 예정일'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='메모'
    )

    def save(self, *args, **kwargs):
        if not self.cycle_number:
            # 해당 그룹의 최대 사이클 번호 + 1
            max_cycle = MedicationCycle.objects.filter(
                group=self.group
            ).aggregate(
                models.Max('cycle_number')
            )['cycle_number__max']
            self.cycle_number = (max_cycle or 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.group.group_name} - Cycle {self.cycle_number}"


class MedicationDetail(BaseModel):
    """복약 상세 정보"""

    class DosageInterval(models.TextChoices):
        HOURLY = 'HOURLY', '시간마다'
        DAILY = 'DAILY', '하루마다'
        WEEKLY = 'WEEKLY', '주마다'
        PRN = 'PRN', '필요시'
        BID = 'BID', '하루 2회'
        TID = 'TID', '하루 3회'
        QID = 'QID', '하루 4회'

    class Meta:
        db_table = 'medication_details'
        verbose_name = '복약 상세'
        verbose_name_plural = '복약 상세들'
        constraints = [
            UniqueConstraint(
                fields=['cycle', 'medication'],
                name='unique_cycle_medication'
            )
        ]

    cycle = models.ForeignKey(
        MedicationCycle,
        on_delete=models.CASCADE,
        related_name='medication_details',
        verbose_name='복약 사이클'
    )
    medication = models.ForeignKey(
        'user.Medication',
        on_delete=models.CASCADE,
        verbose_name='의약품'
    )
    dosage_interval = models.CharField(
        max_length=10,
        choices=DosageInterval.choices,
        default=DosageInterval.DAILY,
        verbose_name='복용 간격'
    )
    frequency_per_interval = models.PositiveIntegerField(
        default=1,
        verbose_name='간격당 복용 횟수'
    )
    quantity_per_dose = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.0,
        verbose_name='회당 복용량'
    )
    total_prescribed = models.PositiveIntegerField(
        verbose_name='총 처방량'
    )
    remaining_quantity = models.PositiveIntegerField(
        verbose_name='잔여량'
    )
    unit = models.CharField(
        max_length=10,
        default='정',
        verbose_name='단위'
    )
    special_instructions = models.TextField(
        blank=True,
        verbose_name='특별 지시사항'
    )

    def save(self, *args, **kwargs):
        if not self.remaining_quantity:
            self.remaining_quantity = self.total_prescribed
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medication.item_name} - {self.quantity_per_dose}{self.unit}"


class MedicationRecord(BaseModel):
    """복약 기록 모델"""

    class RecordType(models.TextChoices):
        TAKEN = 'TAKEN', '복용함'
        MISSED = 'MISSED', '복용 누락'
        SIDE_EFFECT = 'SIDE_EFFECT', '부작용'
        NOTE = 'NOTE', '메모'

    class Meta:
        db_table = 'medication_records'
        verbose_name = '복약 기록'
        verbose_name_plural = '복약 기록들'
        ordering = ['-record_date']

    cycle = models.ForeignKey(
        MedicationCycle,
        on_delete=models.CASCADE,
        related_name='records',
        verbose_name='복약 사이클'
    )
    medication_detail = models.ForeignKey(
        MedicationDetail,
        on_delete=models.CASCADE,
        related_name='records',
        verbose_name='복약 상세'
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
    symptoms = models.TextField(
        blank=True,
        verbose_name='증상 기록'
    )

    def __str__(self):
        return f"{self.medication_detail.medication.item_name} - {self.get_record_type_display()}"


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

    user = models.ForeignKey(
        'user.User',
        on_delete=models.CASCADE,
        related_name='alerts',
        verbose_name='사용자'
    )
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
        return f"{self.user.user_name} - {self.get_alert_type_display()} ({self.alert_time})"