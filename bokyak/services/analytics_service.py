from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, F
from typing import Dict, Any

from bokyak.models.medication_record import MedicationRecord
from bokyak.models.medication_detail import MedicationDetail


class AnalyticsService:
    """복약 통계 및 분석 서비스"""

    @staticmethod
    def get_medication_statistics(user_id: str, days: int = 30) -> Dict[str, Any]:
        """복약 통계 조회"""
        start_date = timezone.now().date() - timedelta(days=days)
        end_date = timezone.now().date()

        records = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_date__range=(start_date, end_date)
        )

        total_records = records.count()
        taken_records = records.filter(record_type='TAKEN').count()
        missed_records = records.filter(record_type='MISSED').count()
        skipped_records = records.filter(record_type='SKIPPED').count()
        side_effect_records = records.filter(record_type='SIDE_EFFECT').count()

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'total_records': total_records,
            'taken_records': taken_records,
            'missed_records': missed_records,
            'skipped_records': skipped_records,
            'side_effect_records': side_effect_records,
            'adherence_rate': (taken_records / total_records * 100) if total_records > 0 else 0
        }

    @staticmethod
    def get_medication_compliance(user_id: str, days: int = 7) -> Dict[str, Any]:
        """복약 순응도 분석"""
        start_date = timezone.now().date() - timedelta(days=days)

        records = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
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
    def get_low_stock_medications(user_id: str, threshold_days: int = 5) -> Dict[str, Any]:
        """잔여량 부족 약물 분석"""
        low_stock = MedicationDetail.objects.filter(
            cycle__group__medical_info__user__user_id=user_id,
            is_active=True,
            remaining_quantity__lte=threshold_days,
            cycle__is_active=True
        ).select_related(
            'medication',
            'cycle__group',
            'cycle__group__medical_info__hospital'
        )

        medications = []
        for detail in low_stock:
            daily_usage = detail.get_daily_usage()  # 일일 사용량
            days_remaining = detail.remaining_quantity / daily_usage if daily_usage > 0 else 0

            medications.append({
                'medication_detail_id': detail.id,
                'medication_name': detail.medication.item_name,
                'remaining_quantity': detail.remaining_quantity,
                'days_remaining': round(days_remaining, 1),
                'hospital_name': detail.cycle.group.medical_info.hospital.hosp_name,
                'group_name': detail.cycle.group.group_name
            })

        return {
            'low_stock_count': len(medications),
            'medications': medications,
            'threshold_days': threshold_days
        }

    @staticmethod
    def get_side_effects_analysis(user_id: str, days: int = 30) -> Dict[str, Any]:
        """부작용 발생 분석"""
        start_date = timezone.now().date() - timedelta(days=days)

        side_effects = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_type='SIDE_EFFECT',
            record_date__date__gte=start_date
        ).select_related(
            'medication_detail__medication'
        ).values(
            'medication_detail__medication__item_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        return {
            'period_days': days,
            'total_side_effects': sum(se['count'] for se in side_effects),
            'side_effects_by_medication': list(side_effects)
        }

    @staticmethod
    def get_medication_timing_analysis(user_id: str, days: int = 30) -> Dict[str, Any]:
        """복약 시간 준수 분석"""
        start_date = timezone.now().date() - timedelta(days=days)

        records = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_type='TAKEN',
            record_date__date__gte=start_date
        ).select_related(
            'medication_detail__medication'
        )

        timing_stats = {
            'morning': {'count': 0, 'on_time': 0},
            'lunch': {'count': 0, 'on_time': 0},
            'evening': {'count': 0, 'on_time': 0},
            'bedtime': {'count': 0, 'on_time': 0}
        }

        time_ranges = {
            'morning': (6, 10),
            'lunch': (11, 14),
            'evening': (17, 20),
            'bedtime': (21, 23)
        }

        for record in records:
            record_time = record.created_at.time()
            for period, (start_hour, end_hour) in time_ranges.items():
                if start_hour <= record_time.hour <= end_hour:
                    timing_stats[period]['count'] += 1
                    if start_hour + 1 <= record_time.hour <= end_hour - 1:
                        timing_stats[period]['on_time'] += 1

        for period in timing_stats:
            count = timing_stats[period]['count']
            timing_stats[period]['on_time_rate'] = (
                (timing_stats[period]['on_time'] / count * 100)
                if count > 0 else 0
            )

        return {
            'period_days': days,
            'timing_stats': timing_stats
        } 