# === 3. 비즈니스 로직 서비스 ===
from datetime import date, timedelta, datetime
from time import timezone
from typing import Dict, Any, List
from django.utils import timezone
from django.db.models import Prefetch, Q

from bokyak.models import MedicationRecord, MedicationDetail
from bokyak.formatters import (
    format_medication_record,
    format_medication_detail,
    format_medication_group
)


class CheckDosageService:
    """복약 체크 서비스"""

    @staticmethod
    def get_today_medication_groups(user_id: str, target_date: datetime.date = None) -> Dict[str, Any]:
        """오늘의 복약 그룹 조회"""
        if not target_date:
            target_date = timezone.now().date()

        # 활성화된 복약 주기 조회
        medication_groups = MedicationDetail.objects.filter(
            cycle__group__medical_info__user__user_id=user_id,
            cycle__is_active=True,
            cycle__start_date__lte=target_date,
            cycle__end_date__gte=target_date,
            is_active=True
        ).select_related(
            'medication',
            'cycle__group',
            'cycle__group__medical_info',
            'cycle__group__medical_info__hospital',
            'cycle__group__medical_info__illness'
        ).prefetch_related(
            'medicationrecord_set'
        )

        # 그룹별로 데이터 정리
        groups_data = {}
        for detail in medication_groups:
            group = detail.cycle.group
            group_id = group.id

            if group_id not in groups_data:
                groups_data[group_id] = {
                    'group': format_medication_group(group),
                    'medications_by_time': {
                        'morning': [],
                        'lunch': [],
                        'evening': [],
                        'bedtime': []
                    },
                    'total_medications': 0,
                    'taken_count': 0,
                    'missed_count': 0
                }

            # 복약 시간대별로 약물 분류
            time_slots = detail.get_time_slots()
            for time_slot in time_slots:
                groups_data[group_id]['medications_by_time'][time_slot].append(
                    format_medication_detail(detail)
                )
                groups_data[group_id]['total_medications'] += 1

            # 복약 기록 확인
            records = detail.medicationrecord_set.filter(record_date=target_date)
            for record in records:
                if record.record_type == 'TAKEN':
                    groups_data[group_id]['taken_count'] += 1
                elif record.record_type == 'MISSED':
                    groups_data[group_id]['missed_count'] += 1

        # 응답 데이터 구성
        total_medications = sum(g['total_medications'] for g in groups_data.values())
        total_taken = sum(g['taken_count'] for g in groups_data.values())
        total_missed = sum(g['missed_count'] for g in groups_data.values())

        return {
            'date': target_date.isoformat(),
            'medication_groups': list(groups_data.values()),
            'total_medications': total_medications,
            'taken_count': total_taken,
            'missed_count': total_missed
        }

    @staticmethod
    def get_next_dosage_time(user_id: str) -> Dict[str, Any]:
        """다음 복약 시간 조회"""
        current_time = timezone.now().time()
        current_date = timezone.now().date()

        # 시간대 우선순위 매핑
        time_ranges = {
            'morning': (6, 10),  # 6시-10시
            'lunch': (11, 14),  # 11시-14시
            'evening': (17, 20),  # 17시-20시
            'bedtime': (21, 23),  # 21시-23시
        }

        # 현재 시간 기준 다음 복약 시간 찾기
        current_hour = current_time.hour
        next_dosage_time = None

        for dosage_time, (start_hour, end_hour) in time_ranges.items():
            if current_hour < start_hour:
                next_dosage_time = dosage_time
                break

        # 오늘 남은 복약 시간이 없으면 내일 아침
        if not next_dosage_time:
            next_dosage_time = 'morning'
            current_date = current_date + timedelta(days=1)

        # 해당 시간대의 복약 데이터 조회
        medication_data = CheckDosageService.get_today_medication_groups(user_id, current_date)

        next_medications = []
        for group in medication_data['medication_groups']:
            if next_dosage_time in group['medications_by_time']:
                next_medications.extend(group['medications_by_time'][next_dosage_time])

        return {
            'next_dosage_time': next_dosage_time,
            'target_date': current_date.isoformat(),
            'medications': next_medications,
            'total_count': len(next_medications)
        }

    @staticmethod
    def create_medication_record(
        user_id: str,
        medication_detail_id: int,
        record_type: str,
        quantity_taken: float = 0.0,
        notes: str = '',
        symptoms: str = None,
        record_date: datetime.date = None
    ) -> MedicationRecord:
        """복약 기록 생성"""
        if not record_date:
            record_date = timezone.now().date()

        # 약물 상세 정보 조회 및 권한 확인
        medication_detail = MedicationDetail.objects.get(
            id=medication_detail_id,
            cycle__group__medical_info__user__user_id=user_id
        )

        # 복약 기록 생성
        record = MedicationRecord.objects.create(
            medication_detail=medication_detail,
            record_type=record_type,
            quantity_taken=quantity_taken,
            notes=notes,
            symptoms=symptoms,
            record_date=record_date
        )

        # 잔여량 업데이트
        if record_type == 'TAKEN':
            medication_detail.remaining_quantity = max(0, medication_detail.remaining_quantity - quantity_taken)
            medication_detail.save()

        return record

    @staticmethod
    def create_bulk_medication_records(user_id: str, records_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """복수 복약 기록 생성"""
        created_records = []
        failed_records = []

        for record_data in records_data:
            try:
                record = CheckDosageService.create_medication_record(
                    user_id=user_id,
                    medication_detail_id=record_data['medication_detail_id'],
                    record_type=record_data['record_type'],
                    quantity_taken=record_data.get('quantity_taken', 0.0),
                    notes=record_data.get('notes', ''),
                    symptoms=record_data.get('symptoms'),
                    record_date=record_data.get('record_date')
                )
                created_records.append(record)
            except Exception as e:
                failed_records.append({
                    'data': record_data,
                    'error': str(e)
                })

        return {
            'created_records': created_records,
            'failed_records': failed_records,
            'success_count': len(created_records),
            'fail_count': len(failed_records)
        }

    @staticmethod
    def get_medication_records(
        user_id: str,
        start_date: datetime.date,
        end_date: datetime.date,
        medication_detail_id: int = None
    ) -> List[Dict[str, Any]]:
        """복약 기록 조회"""
        records = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_date__range=(start_date, end_date)
        )

        if medication_detail_id:
            records = records.filter(medication_detailid=medication_detail_id)

        records = records.select_related(
            'medication_detail',
            'medication_detail__medication'
        ).order_by('-record_date', '-created_at')

        return [format_medication_record(record) for record in records]