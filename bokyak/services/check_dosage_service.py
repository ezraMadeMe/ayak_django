# === 3. 비즈니스 로직 서비스 ===
from datetime import date, timedelta
from time import timezone

from django.db.models import Prefetch

from bokyak.models import MedicationRecord, MedicationDetail, MedicationCycle, MedicationGroup
from user.models import Medication, UserMedicalInfo


class CheckDosageService:
    @staticmethod
    def get_today_medication_groups(user_id: str, target_date: date = None) -> dict:

        try:
            # 1. 사용자의 활성 의료 정보 조회
            user_medical_infos = UserMedicalInfo.objects.filter(
                user_id=user_id,
                is_primary=True
            ).select_related('hospital', 'illness', 'prescription')

            if not user_medical_infos.exists():
                return CheckDosageService._empty_response(user_id, target_date)

            result_groups = []

            # 2. 각 의료 정보에 대한 복약그룹 조회
            for medical_info in user_medical_infos:
                medication_groups = MedicationGroup.objects.filter(
                    medical_info=medical_info
                ).prefetch_related(
                    Prefetch(
                        'medicationcycle_set',
                        queryset=MedicationCycle.objects.filter(
                            is_active=True,
                            cycle_start__lte=target_date,
                            cycle_end__gte=target_date
                        ).prefetch_related(
                            Prefetch(
                                'medicationdetail_set',
                                queryset=MedicationDetail.objects.select_related(
                                    'prescription_medication__medication'
                                )
                            )
                        )
                    )
                )

                for group in medication_groups:
                    active_cycles = group.medicationcycle_set.all()

                    if not active_cycles:
                        continue

                    # 가장 최근 활성 주기 선택
                    active_cycle = active_cycles.first()

                    group_data = CheckDosageService._process_medication_group(
                        group, active_cycle, target_date
                    )

                    if group_data:
                        result_groups.append(group_data)

            return {
                'user_id': user_id,
                'today_date': target_date,
                'medication_groups': result_groups,
                'overall_stats': CheckDosageService._calculate_overall_stats(result_groups),
            }

        except Exception as e:
            print(f"Error in get_today_medication_groups: {str(e)}")
            return CheckDosageService._empty_response(user_id, target_date)

    @staticmethod
    def create_bulk_medication_records(user_id: str, records_data: list):
        created_records = []
        failed_records = []

        for record_data in records_data:
            try:
                record = CheckDosageService.create_medication_record(
                    user_id=user_id,
                    medication_detail_id=record_data['medication_detail_id'],
                    record_type=record_data['record_type'],
                    quantity_taken=record_data.get('quantity_taken', 0.0),
                    notes=record_data.get('notes', '')
                )
                created_records.append(record)

            except Exception as e:
                failed_records.append({
                    'medication_detail_id': record_data.get('medication_detail_id'),
                    'error': str(e)
                })

        return {
            'created_records': created_records,
            'failed_records': failed_records,
            'total_requested': len(records_data),
            'total_created': len(created_records),
            'total_failed': len(failed_records)
        }

    @staticmethod
    def get_next_dosage_time(user_id: str):
        current_time = timezone.now()
        current_date = current_time.date()
        current_hour = current_time.hour

        # 시간대 범위 정의
        time_ranges = {
            'morning': (6, 10),
            'lunch': (11, 14),
            'evening': (17, 20),
            'bedtime': (21, 23),
        }

        # 다음 복약 시간 찾기
        next_dosage_time = None
        target_date = current_date

        for dosage_time, (start_hour, end_hour) in time_ranges.items():
            if current_hour < start_hour:
                next_dosage_time = dosage_time
                break

        # 오늘 남은 시간이 없으면 내일 아침
        if not next_dosage_time:
            next_dosage_time = 'morning'
            target_date = current_date + timedelta(days=1)

        # 해당 시간대의 복약 데이터 조회
        medication_data = CheckDosageService.get_today_medication_groups(user_id, target_date)

        next_medications = []
        for group in medication_data['medication_groups']:
            if next_dosage_time in group['medications_by_time']:
                next_medications.extend(group['medications_by_time'][next_dosage_time])

        return {
            'next_dosage_time': next_dosage_time,
            'target_date': target_date,
            'medications': next_medications,
            'total_count': len(next_medications)
        }

    @staticmethod
    def _empty_response(user_id: str, target_date: date):
        return {
            'user_id': user_id,
            'today_date': target_date,
            'medication_groups': [],
            'overall_stats': {
                'total_medications': 0,
                'total_taken': 0,
                'total_missed': 0,
                'overall_completion_rate': 0,
            },
        }

    @staticmethod
    def _process_medication_group(group, cycle, target_date):
        medication_details = cycle.medicationdetail_set.all()

        if not medication_details:
            return None

        medications_by_time = {}
        dosage_times = set()

        for detail in medication_details:
            dosage_pattern = detail.actual_dosage_pattern

            # dosage_pattern 예시: {"morning": {"enabled": true, "quantity": 1, "unit": "mg"}}
            for time_key, time_data in dosage_pattern.items():
                if time_data.get('enabled', False):
                    dosage_times.add(time_key)

                    if time_key not in medications_by_time:
                        medications_by_time[time_key] = []

                    # 오늘의 복약 기록 확인
                    today_record = MedicationRecord.objects.filter(
                        medication_detail=detail,
                        record_date__date=target_date
                    ).first()

                    medication_item = {
                        'medication_detail_id': detail.id,
                        'medication': {
                            'item_seq': detail.prescription_medication.medication.item_seq,
                            'item_name': detail.prescription_medication.medication.item_name,
                            'entp_name': detail.prescription_medication.medication.entp_name,
                            'item_image': detail.prescription_medication.medication.item_image,
                            'class_name': detail.prescription_medication.medication.class_name,
                            'dosage_form': detail.prescription_medication.medication.dosage_form,
                            'is_prescription': detail.prescription_medication.medication.is_prescription,
                        },
                        'dosage_time': time_key,
                        'quantity_per_dose': float(time_data.get('quantity', 1)),
                        'unit': time_data.get('unit', 'mg'),
                        'special_instructions': time_data.get('instructions', ''),
                        'is_taken_today': today_record is not None,
                        'taken_at': today_record.record_date if today_record else None,
                        'record_type': today_record.record_type if today_record else None,
                    }

                    medications_by_time[time_key].append(medication_item)

        if not dosage_times:
            return None

        # 완료 현황 계산
        completion_status = {}
        for time_key, medications in medications_by_time.items():
            total = len(medications)
            taken = len([m for m in medications if m['is_taken_today']])
            completion_status[time_key] = {
                'total': total,
                'taken': taken,
                'completion_rate': taken / total if total > 0 else 0
            }

        # 시간대 정렬
        time_priority = {'morning': 1, 'lunch': 2, 'evening': 3, 'bedtime': 4, 'prn': 5}
        sorted_times = sorted(dosage_times, key=lambda x: time_priority.get(x, 99))

        return {
            'group_id': group.group_id,
            'group_name': group.group_name,
            'cycle_id': cycle.id,
            'cycle_number': cycle.cycle_number,
            'dosage_times': sorted_times,
            'medications_by_time': medications_by_time,
            'completion_status': completion_status,
        }


    @staticmethod
    def _calculate_overall_stats(groups: list) -> dict:
        """전체 복약 통계 계산"""
        total_medications = 0
        total_taken = 0

        for group in groups:
            for time_key, status in group['completion_status'].items():
                total_medications += status['total']
                total_taken += status['taken']

        return {
            'total_medications': total_medications,
            'total_taken': total_taken,
            'total_missed': total_medications - total_taken,
            'overall_completion_rate': total_taken / total_medications if total_medications > 0 else 0,
        }

    @staticmethod
    def create_medication_record(user_id: str, medication_detail_id: int,
                                 record_type: str, quantity_taken: float = 0.0,
                                 notes: str = '') -> MedicationRecord:

        # 1. 권한 확인
        try:
            medication_detail = MedicationDetail.objects.select_related(
                'cycle__group__medical_info__user'
            ).get(id=medication_detail_id)

            if medication_detail.cycle.group.medical_info.user.user_id != user_id:
                raise PermissionError("해당 복약 정보에 대한 권한이 없습니다.")

        except MedicationDetail.DoesNotExist:
            raise ValueError("존재하지 않는 복약 상세 정보입니다.")

        # 2. 오늘 기록 확인/업데이트
        today = timezone.now().date()
        record, created = MedicationRecord.objects.update_or_create(
            medication_detail_id=medication_detail_id,
            record_date__date=today,
            defaults={
                'record_type': record_type,
                'quantity_taken': quantity_taken,
                'notes': notes,
                'record_date': timezone.now(),
            }
        )

        return record