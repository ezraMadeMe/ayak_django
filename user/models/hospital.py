from django.db import models
from django.db.models import UniqueConstraint

from common.models.base_model import BaseModel, CodeGeneratorMixin
from user.models.ayakuser import AyakUser


class Hospital(BaseModel, CodeGeneratorMixin):
    """병원 정보 모델"""

    class Meta:
        db_table = 'hospitals'
        verbose_name = '병원'
        verbose_name_plural = '병원들'
        constraints = [
            UniqueConstraint(
                fields=['user', 'hosp_code'],
                name='unique_user_hospital'
            )
        ]

    hospital_id = models.CharField(
        primary_key=True,
        max_length=8,
        editable=False,
        verbose_name='병원 등록 코드'
    )
    user = models.ForeignKey(
        AyakUser,
        on_delete=models.CASCADE,
        related_name='hospitals',
        verbose_name='사용자'
    )
    hosp_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='병원 코드'
    )
    hosp_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='병원명'
    )
    hosp_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='병원 종별'
    )
    doctor_name = models.CharField(
        max_length=30,
        blank=True,
        verbose_name='담당의'
    )
    address = models.TextField(
        blank=True,
        verbose_name='병원 주소'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='전화번호'
    )

    def save(self, *args, **kwargs):
        if not self.hospital_id:
            self.hospital_id = self.generate_unique_code(
                Hospital, 'hospital_id'
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hosp_name} - {self.doctor_name}"