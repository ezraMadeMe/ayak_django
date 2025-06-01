# bokyak/signals.py 파일 생성
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models.medication_record import MedicationRecord
from .models.prescription import Prescription


@receiver(post_save, sender=MedicationRecord)
def update_remaining_quantity(sender, instance, created, **kwargs):
    """복약 기록 생성 시 잔여량 업데이트"""
    if created and instance.record_type == MedicationRecord.RecordType.TAKEN:
        detail = instance.medication_detail
        detail.remaining_quantity = max(0, detail.remaining_quantity - instance.quantity_taken)
        detail.save(update_fields=['remaining_quantity'])


@receiver(post_save, sender=Prescription)
def deactivate_previous_prescriptions(sender, instance, created, **kwargs):
    """새 처방전 생성 시 이전 처방전들 비활성화"""
    # if created:
    #     # 같은 의료정보의 다른 활성 처방전들 비활성화
    #     Prescription.objects.filter(
    #         medical_info=instance.medical_info,
    #         is_active=True
    #     ).exclude(prescription_id=instance.prescription_id).update(is_active=False)
