from django.db import models
from django.db.models import UniqueConstraint

from bokyak.models.medication_group import MedicationGroup
from common.models.base_model import BaseModel


class MedicationCycle(BaseModel):
    """복약 주기 모델"""

    class Meta:
        db_table = 'medication_cycles'
        verbose_name = '복약 주기'
        verbose_name_plural = '복약 주기들'
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
        verbose_name='주기 번호'
    )
    cycle_start = models.DateField(
        verbose_name='처방일'
    )
    cycle_end = models.DateField(
        blank=True,
        null=True,
        verbose_name='다음 방문 예정일'
    )
    # 복약그룹 상태
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성 상태'
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
        return f"{self.group.medical_info.user.user_name} - {self.group.group_name} - 주기 {self.cycle_number}"

