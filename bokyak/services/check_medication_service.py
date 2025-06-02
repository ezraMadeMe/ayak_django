# === 3. 비즈니스 로직 서비스 ===
from datetime import date
from time import timezone

from bokyak.models import MedicationRecord, MedicationDetail, MedicationCycle, MedicationGroup
from user.models import Medication, UserMedicalInfo


class MedicationService:
    @staticmethod
    def get_today_medication_groups(user_id: str, target_date: date = None) -> dict:
        """사용자의 오늘 복약그룹 데이터 조회"""
        if target_date is None:
            target_date = timezone.now().date()

        # 1. 활성 복약그룹 조회
        active_groups = MedicationGroup.objects.filter(
            medical_info_id__in=UserMedicalInfo.objects.filter(
                user_id=user_id, is_primary=True
            ).values_list('id', flat=True)
        )

        result_groups = []

        for group in active_groups:
            # 2. 현재 활성 주기 조회
            active_cycle = MedicationCycle.objects.filter(
                group_id=group.group_id,
                is_active=True,
                cycle_start__lte=target_date,
                cycle_end__gte=target_date
            ).first()

            if not active_cycle:
                continue

            # 3. 해당 주기의 복약 상세 정보 조회
            medication_details = MedicationDetail.objects.filter(
                cycle_id=active_cycle.id
            )

            # 4. 시간대별로 약물 분류
            medications_by_time = {}
            dosage_times = set()

            for detail in medication_details:
                dosage_pattern = detail.actual_dosage_pattern

                for time_key, time_data in dosage_pattern.items():
                    if time_data.get('enabled', False):
                        dosage_times.add(time_key)

                        if time_key not in medications_by_time:
                            medications_by_time[time_key] = []

                        # 5. 오늘의 복약 기록 확인
                        today_record = MedicationRecord.objects.filter(
                            medication_detail_id=detail.id,
                            record_date__date=target_date
                        ).first()

                        # 6. 약물 기본 정보 조회
                        medication = Medication.objects.get(
                            item_seq=detail.prescription_medication_id
                        )

                        medication_item = {
                            'medication_detail_id': detail.id,
                            'medication': {
                                'item_seq': medication.item_seq,
                                'item_name': medication.item_name,
                                'entp_name': medication.entp_name,
                                'item_image': medication.item_image,
                                'class_name': medication.class_name,
                                'dosage_form': medication.dosage_form,
                                'is_prescription': medication.is_prescription,
                            },
                            'dosage_time': time_key,
                            'quantity_per_dose': time_data.get('quantity', 1),
                            'unit': time_data.get('unit', 'mg'),
                            'special_instructions': time_data.get('instructions', ''),
                            'is_taken_today': today_record is not None,
                            'taken_at': today_record.record_date if today_record else None,
                            'record_type': today_record.record_type if today_record else None,
                        }

                        medications_by_time[time_key].append(medication_item)

            # 7. 완료 현황 계산
            completion_status = {}
            for time_key, medications in medications_by_time.items():
                total = len(medications)
                taken = len([m for m in medications if m['is_taken_today']])
                completion_status[time_key] = {
                    'total': total,
                    'taken': taken,
                    'completion_rate': taken / total if total > 0 else 0
                }

            # 8. 우선순위에 따른 정렬
            time_priority = {'morning': 1, 'lunch': 2, 'evening': 3, 'bedtime': 4, 'prn': 5}
            sorted_times = sorted(dosage_times, key=lambda x: time_priority.get(x, 99))

            group_data = {
                'group_id': group.group_id,
                'group_name': group.group_name,
                'cycle_id': active_cycle.id,
                'cycle_number': active_cycle.cycle_number,
                'dosage_times': sorted_times,
                'medications_by_time': medications_by_time,
                'completion_status': completion_status,
            }

            result_groups.append(group_data)

        return {
            'user_id': user_id,
            'today_date': target_date,
            'medication_groups': result_groups,
            'overall_stats': MedicationService._calculate_overall_stats(result_groups),
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
        """복약 기록 생성"""

        # 1. 권한 확인 (해당 medication_detail이 사용자 소유인지)
        medication_detail = MedicationDetail.objects.get(id=medication_detail_id)
        cycle = MedicationCycle.objects.get(id=medication_detail.cycle_id)
        group = MedicationGroup.objects.get(group_id=cycle.group_id)

        # 사용자 권한 확인 로직 (실제 구현 시 추가)

        # 2. 오늘 기록이 이미 있는지 확인
        today = timezone.now().date()
        existing_record = MedicationRecord.objects.filter(
            medication_detail_id=medication_detail_id,
            record_date__date=today
        ).first()

        if existing_record:
            # 기존 기록 업데이트
            existing_record.record_type = record_type
            existing_record.quantity_taken = quantity_taken
            existing_record.notes = notes
            existing_record.record_date = timezone.now()
            existing_record.save()
            return existing_record
        else:
            # 새 기록 생성
            record = MedicationRecord.objects.create(
                medication_detail_id=medication_detail_id,
                record_type=record_type,
                record_date=timezone.now(),
                quantity_taken=quantity_taken,
                notes=notes
            )
            return record