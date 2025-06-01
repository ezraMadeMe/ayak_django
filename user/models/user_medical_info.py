from django.db import models
from django.db.models import UniqueConstraint
from rest_framework.exceptions import ValidationError

from bokyak.models.prescription import Prescription
from common.models.base_model import BaseModel
from user.models.hospital import Hospital
from user.models.illness import Illness
from user.models.ayakuser import AyakUser


class UserMedicalInfo(BaseModel):
    """사용자 의료 정보 (병원+질병 연결)"""

    class Meta:
        db_table = 'user_medical_info'
        verbose_name = '사용자 의료정보'
        verbose_name_plural = '사용자 의료정보들'
        constraints = [
            UniqueConstraint(
                fields=['user', 'hospital', 'illness'],
                name='unique_user_medical_info'
            )
        ]

    user = models.ForeignKey(
        AyakUser,
        on_delete=models.CASCADE,
        related_name='medical_info',
        verbose_name='사용자'
    )
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        verbose_name='병원'
    )
    illness = models.ForeignKey(
        Illness,
        on_delete=models.CASCADE,
        verbose_name='질병/증상'
    )
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='user_prescription',
        verbose_name='처방전(is_active=True인 처방이 업데이트)'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='즐겨찾기 여부'
    )

    def clean(self):
        """데이터 유효성 검증"""
        super().clean()

        if self.prescription:
            # 같은 처방전을 공유하는 다른 의료정보들 확인
            other_medical_infos = UserMedicalInfo.objects.filter(
                prescription=self.prescription
            ).exclude(id=self.id)

            for other in other_medical_infos:
                # 같은 사용자, 같은 병원인지 확인
                if other.user != self.user or other.hospital != self.hospital:
                    raise ValidationError(
                        "처방전은 같은 사용자의 같은 병원 내에서만 공유 가능합니다."
                    )

    def __str__(self):
        return f"{self.user.user_name} - {self.hospital.hosp_name} - {self.illness.ill_name}"

