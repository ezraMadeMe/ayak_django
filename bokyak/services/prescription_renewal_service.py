# models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

from bokyak.models.medication_alert import MedicationAlert
from bokyak.models.medication_cycle import MedicationCycle
from bokyak.models.medication_detail import MedicationDetail
from bokyak.models.medication_group import MedicationGroup
from bokyak.models.prescription import Prescription
from bokyak.models.prescription_medication import PrescriptionMedication
from user.models import UserMedicalInfo


class PrescriptionRenewalService:
    """처방전 갱신 및 주기 관리 서비스"""

    @staticmethod
    def renew_prescription(user_id, hospital_id, illness_id, old_prescription_id,
                           prescription_date, medications_data):
        """
        처방전 갱신 처리
        - 기존 주기 종료
        - 새 처방전 생성
        - 새 주기 자동 생성
        """
        from django.db import transaction

        with transaction.atomic():
            # 1. 새 처방전 생성
            new_prescription = Prescription.objects.create(
                prescription_id=f"PRESC_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                prescription_date=prescription_date,
                previous_prescription_id=old_prescription_id,
                is_active=True
            )

            # 2. 기존 처방전 비활성화
            if old_prescription_id:
                Prescription.objects.filter(
                    prescription_id=old_prescription_id
                ).update(is_active=False)

                # 기존 활성 주기들 종료
                MedicationCycle.objects.filter(
                    medication_groups__user_medical_info__prescription_id=old_prescription_id,
                    is_active=True
                ).update(
                    is_active=False,
                    cycle_end=timezone.now().date()
                )

            # 3. 의료 정보 업데이트/생성
            medical_info, created = UserMedicalInfo.objects.get_or_create(
                user_id=user_id,
                hospital_id=hospital_id,
                illness_id=illness_id,
                defaults={
                    'prescription_id': new_prescription.prescription_id,
                    'is_primary': True
                }
            )

            if not created:
                medical_info.prescription_id = new_prescription.prescription_id
                medical_info.save()

            # 4. 처방전 약물 정보 저장
            for med_data in medications_data:
                PrescriptionMedication.objects.create(
                    prescription_id=new_prescription.prescription_id,
                    medication_id=med_data['medication_id'],
                    standard_dosage_pattern=med_data['dosage_pattern'],
                    cycle_total_quantity=med_data['total_quantity'],
                    duration_days=med_data['duration_days'],
                    total_quantity=med_data['total_quantity']
                )

            # 5. 새 복약 그룹 생성
            new_group = MedicationGroup.objects.create(
                group_id=f"GROUP_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                medical_info_id=medical_info.id,
                prescription_id=new_prescription.prescription_id,
                group_name=f"복약그룹 {prescription_date}",
                reminder_enabled=True
            )

            # 6. 새 주기 자동 생성
            PrescriptionRenewalService.create_new_cycle(
                new_group.group_id,
                prescription_date,
                medications_data
            )

            return {
                'prescription_id': new_prescription.prescription_id,
                'group_id': new_group.group_id,
                'medical_info_id': medical_info.id
            }

    @staticmethod
    def create_new_cycle(group_id, start_date, medications_data):
        """새 복약 주기 생성"""
        from django.db import transaction

        with transaction.atomic():
            # 최대 처방일수 계산
            max_duration = max([med['duration_days'] for med in medications_data])
            cycle_end_date = start_date + timedelta(days=max_duration)

            # 기존 주기 개수 확인하여 cycle_number 설정
            existing_cycles_count = MedicationCycle.objects.filter(
                group_id=group_id
            ).count()

            # 새 주기 생성
            new_cycle = MedicationCycle.objects.create(
                group_id=group_id,
                cycle_number=existing_cycles_count + 1,
                cycle_start=start_date,
                cycle_end=cycle_end_date,
                is_active=True
            )

            # 각 처방약물에 대한 상세 정보 생성
            prescription_medications = PrescriptionMedication.objects.filter(
                prescription__medicationgroup__group_id=group_id
            )

            for presc_med in prescription_medications:
                medication_detail = MedicationDetail.objects.create(
                    cycle_id=new_cycle.id,
                    prescription_medication_id=presc_med.id,
                    actual_dosage_pattern=presc_med.standard_dosage_pattern,
                    remaining_quantity=presc_med.cycle_total_quantity,
                    patient_adjustments={}
                )

                # 기본 알림 설정 생성
                PrescriptionRenewalService.create_default_alerts(medication_detail.id)

            return new_cycle

    @staticmethod
    def create_default_alerts(medication_detail_id):
        """기본 복약 알림 생성"""
        default_alert_times = ['08:00', '12:00', '18:00', '22:00']

        for alert_time in default_alert_times:
            MedicationAlert.objects.create(
                medication_detail_id=medication_detail_id,
                alert_type='DAILY',
                alert_time=alert_time,
                is_active=True,
                message='복약 시간입니다.'
            )