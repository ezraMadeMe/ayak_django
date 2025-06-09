# bokyak/services/reminder_service.py
from django.utils import timezone
from datetime import timedelta, time, datetime
from ..models.medication_record import MedicationRecord, MedicationDetail
from ..models.medication_alert import MedicationAlert
from typing import Dict, Any, List
from django.db.models import Q, F
from bokyak.formatters import format_medication_alert


class MedicationReminderService:
    """복약 알림 서비스"""

    @staticmethod
    def get_active_alerts(user_id: str) -> List[Dict[str, Any]]:
        """활성화된 알림 목록 조회"""
        alerts = MedicationAlert.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            is_active=True
        ).select_related(
            'medication_detail',
            'medication_detail__medication'
        ).order_by('alert_time')

        return [format_medication_alert(alert) for alert in alerts]

    @staticmethod
    def create_alert(
        user_id: str,
        medication_detail_id: int,
        alert_time: str,
        alert_type: str,
        message: str = None
    ) -> Dict[str, Any]:
        """알림 생성"""
        medication_detail = MedicationDetail.objects.get(
            id=medication_detail_id,
            cycle__group__medical_info__user__user_id=user_id
        )

        alert = MedicationAlert.objects.create(
            medication_detail=medication_detail,
            alert_time=datetime.strptime(alert_time, '%H:%M').time(),
            alert_type=alert_type,
            message=message or f'{medication_detail.medication.item_name} 복용 시간입니다.'
        )

        return format_medication_alert(alert)

    @staticmethod
    def update_alert(
        user_id: str,
        alert_id: int,
        alert_time: str = None,
        alert_type: str = None,
        message: str = None,
        is_active: bool = None
    ) -> Dict[str, Any]:
        """알림 수정"""
        alert = MedicationAlert.objects.get(
            id=alert_id,
            medication_detail__cycle__group__medical_info__user__user_id=user_id
        )

        if alert_time:
            alert.alert_time = datetime.strptime(alert_time, '%H:%M').time()
        if alert_type:
            alert.alert_type = alert_type
        if message:
            alert.message = message
        if is_active is not None:
            alert.is_active = is_active

        alert.save()
        return format_medication_alert(alert)

    @staticmethod
    def delete_alert(user_id: str, alert_id: int) -> bool:
        """알림 삭제"""
        alert = MedicationAlert.objects.get(
            id=alert_id,
            medication_detail__cycle__group__medical_info__user__user_id=user_id
        )
        alert.delete()
        return True

    @staticmethod
    def get_upcoming_alerts(user_id: str, minutes: int = 30) -> List[Dict[str, Any]]:
        """다가오는 알림 목록 조회"""
        now = timezone.now()
        target_time = (now + timedelta(minutes=minutes)).time()

        # 현재 시간부터 지정된 시간 범위 내의 알림 조회
        alerts = MedicationAlert.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            is_active=True,
            alert_time__gte=now.time(),
            alert_time__lte=target_time
        ).select_related(
            'medication_detail',
            'medication_detail__medication'
        ).order_by('alert_time')

        return [format_medication_alert(alert) for alert in alerts]

    @staticmethod
    def get_low_stock_alerts(user_id: str, threshold_days: int = 5) -> List[Dict[str, Any]]:
        """잔여량 부족 알림 조회"""
        low_stock = MedicationDetail.objects.filter(
            cycle__group__medical_info__user__user_id=user_id,
            is_active=True,
            remaining_quantity__lte=F('dosage') * F('times_per_day') * threshold_days,
            cycle__is_active=True
        ).select_related(
            'medication',
            'cycle__group',
            'cycle__group__medical_info__hospital'
        )

        alerts = []
        for detail in low_stock:
            daily_usage = detail.get_daily_usage()
            days_remaining = detail.remaining_quantity / daily_usage if daily_usage > 0 else 0

            alerts.append({
                'medication_detail_id': detail.id,
                'medication_name': detail.medication.item_name,
                'remaining_quantity': detail.remaining_quantity,
                'days_remaining': round(days_remaining, 1),
                'hospital_name': detail.cycle.group.medical_info.hospital.hosp_name,
                'group_name': detail.cycle.group.group_name,
                'alert_type': 'LOW_STOCK',
                'message': f'{detail.medication.item_name}의 잔여량이 {round(days_remaining, 1)}일분 남았습니다.'
            })

        return alerts

    @staticmethod
    def get_compliance_alerts(user_id: str, days: int = 7, threshold: float = 80.0) -> List[Dict[str, Any]]:
        """복약 순응도 알림 조회"""
        from bokyak.services.analytics_service import AnalyticsService

        compliance_data = AnalyticsService.get_medication_compliance(user_id, days)
        alerts = []

        if compliance_data['compliance_rate'] < threshold:
            alerts.append({
                'alert_type': 'LOW_COMPLIANCE',
                'message': (
                    f'최근 {days}일간 복약 순응도가 {compliance_data["compliance_rate"]}%로 '
                    f'목표치({threshold}%)보다 낮습니다. 복약 관리에 더 신경 써주세요.'
                )
            })

        return alerts

    @staticmethod
    def get_all_alerts(user_id: str) -> Dict[str, Any]:
        """모든 종류의 알림 통합 조회"""
        upcoming = MedicationReminderService.get_upcoming_alerts(user_id)
        low_stock = MedicationReminderService.get_low_stock_alerts(user_id)
        compliance = MedicationReminderService.get_compliance_alerts(user_id)

        return {
            'upcoming_alerts': upcoming,
            'low_stock_alerts': low_stock,
            'compliance_alerts': compliance,
            'total_alerts': len(upcoming) + len(low_stock) + len(compliance)
        }

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