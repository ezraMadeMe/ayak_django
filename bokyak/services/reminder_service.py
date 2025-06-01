# bokyak/services/reminder_service.py
from django.utils import timezone
from datetime import timedelta, time
from ..models.medication_record import MedicationRecord, MedicationDetail
from ..models.medication_alert import MedicationAlert


class MedicationReminderService:
    """복약 알림 서비스"""

    @staticmethod
    def get_pending_medications(user, target_time=None):
        """특정 시간에 복용해야 할 약물들 조회"""
        if target_time is None:
            target_time = timezone.now().time()

        # 활성 알림들 중 해당 시간에 맞는 것들
        alerts = MedicationAlert.objects.filter(
            medication_detail__cycle__group__medical_info__user=user,
            medication_detail__is_active=True,
            medication_detail__cycle__is_active=True,
            is_active=True,
            alert_type=MedicationAlert.AlertType.DOSAGE,
            alert_time=target_time
        ).select_related(
            'medication_detail__medication',
            'medication_detail__cycle__group'
        )

        return alerts

    @staticmethod
    def check_medication_compliance(user, days=7):
        """복약 순응도 체크"""
        start_date = timezone.now().date() - timedelta(days=days)

        # 해당 기간의 복약 기록들
        records = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user=user,
            record_date__date__gte=start_date
        )

        total_records = records.count()
        taken_records = records.filter(
            record_type=MedicationRecord.RecordType.TAKEN
        ).count()

        compliance_rate = (taken_records / total_records * 100) if total_records > 0 else 0

        return {
            'total_records': total_records,
            'taken_records': taken_records,
            'compliance_rate': round(compliance_rate, 2),
            'period_days': days
        }

    @staticmethod
    def get_refill_notifications(user):
        """처방전 갱신 알림이 필요한 약물들"""
        # 잔여량이 5일치 이하인 약물들
        low_stock = MedicationDetail.objects.filter(
            cycle__group__medical_info__user=user,
            is_active=True,
            remaining_quantity__lte=5,
            cycle__is_active=True
        ).select_related('medication', 'cycle__group')

        return low_stock