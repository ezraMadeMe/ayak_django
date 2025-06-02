# management/commands/create_psychiatric_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date, timedelta
import json
import random

from user.models import (
    AyakUser, Hospital, Illness, MainIngredient, Medication,
    MedicationIngredient, UserMedicalInfo
)
from bokyak.models import (
    Prescription, PrescriptionMedication, MedicationGroup, MedicationCycle,
    MedicationDetail, MedicationRecord, MedicationAlert
)

class Command(BaseCommand):
    help = '정신과 환자 더미데이터 생성'

    def handle(self, *args, **options):
        # 기존 데이터 삭제 (선택사항)
        if input("기존 데이터를 모두 삭제하시겠습니까? (y/N): ").lower() == 'y':
            self.clear_existing_data()

        # 현재 날짜 기준으로 3개월 전부터 데이터 생성
        current_date = timezone.now()
        start_date = current_date - timedelta(days=90)

        # 1. 사용자 생성
        user = AyakUser.objects.create(
            user_id="USR_PSYCH_001",
            user_name="김정신",
            join_date=start_date - timedelta(days=30),
            push_agree=True,
            is_active=True
        )
        self.stdout.write(f"✅ 사용자 생성: {user.user_name}")

        # 2. 병원 정보
        hospital = Hospital.objects.create(
            hospital_id="HOSP_001",
            user=user,
            hosp_code="PSYCH001",
            hosp_name="서울대학교병원 정신건강의학과",
            hosp_type="상급종합병원",
            doctor_name="이정신",
            address="서울특별시 종로구 대학로 101",
            phone_number="02-2072-2972"
        )
        self.stdout.write(f"✅ 병원 등록: {hospital.hosp_name}")

        # 3. 질병 정보
        illnesses_data = [
            ("ILL_ADHD_001", "DISEASE", "주의력결핍 과잉행동장애", "F90.0", start_date - timedelta(days=365)),
            ("ILL_BIPOLAR_001", "DISEASE", "양극성 정동장애", "F31.9", start_date - timedelta(days=180)),
            ("ILL_ANXIETY_001", "DISEASE", "일반화불안장애", "F41.1", start_date - timedelta(days=90))
        ]

        illnesses = []
        for ill_id, ill_type, ill_name, ill_code, ill_start in illnesses_data:
            illness = Illness.objects.create(
                illness_id=ill_id,
                user=user,
                ill_type=ill_type,
                ill_name=ill_name,
                ill_code=ill_code,
                ill_start=ill_start.date(),
                is_chronic=True
            )
            illnesses.append(illness)
        self.stdout.write(f"✅ 질병 등록: {len(illnesses)}개")

        # 4. 주성분 정보
        ingredients_data = [
            ("INGR_METHYLPHENIDATE", "METH001", "TAB", "정제", "메틸페니데이트염산염", "Methylphenidate HCl", 1117, "경구", 18.0,
             "mg"),
            ("INGR_VALPROATE", "VALP001", "TAB", "서방정", "발프로산나트륨", "Sodium Valproate", 1143, "경구", 500.0, "mg"),
            ("INGR_QUETIAPINE", "QUET001", "TAB", "서방정", "퀘티아핀푸마르산염", "Quetiapine Fumarate", 1171, "경구", 200.0, "mg"),
            ("INGR_ALPRAZOLAM", "ALPR001", "TAB", "정제", "알프라졸람", "Alprazolam", 1124, "경구", 0.25, "mg")
        ]

        ingredients = []
        for ingr_code, orig_code, dosage_form_code, dosage_form, name_kr, name_en, class_code, route, density, unit in ingredients_data:
            ingredient = MainIngredient.objects.create(
                ingr_code=ingr_code,
                original_code=orig_code,
                dosage_form_code=dosage_form_code,
                dosage_form=dosage_form,
                main_ingr_name_kr=name_kr,
                main_ingr_name_en=name_en,
                classification_code=class_code,
                administration_route=route,
                main_ingr_density=density,
                main_ingr_unit=unit,
                original_density_text=f"{density}{unit}",
                is_combination=False,
                is_active=True,
                notes="정신과 약물",
                data_quality_score=95
            )
            ingredients.append(ingredient)
        self.stdout.write(f"✅ 주성분 등록: {len(ingredients)}개")

        # 5. 의약품 정보
        medications_data = [
            (200001, "콘서타서방정18밀리그램", "한국얀센", "concerta_18mg.jpg", "중추신경계용약", "서방정", True),
            (200002, "데파코트서방정500밀리그램", "한국애브비", "depakote_500mg.jpg", "항전간제", "서방정", True),
            (200003, "쎄로켈서방정200밀리그램", "한국아스트라제네카", "seroquel_200mg.jpg", "항정신병약", "서방정", True),
            (200004, "자낙스정0.25밀리그램", "한국화이자", "xanax_025mg.jpg", "항불안제", "정제", True)
        ]

        medications = []
        for item_seq, item_name, entp_name, item_image, class_name, dosage_form, is_prescription in medications_data:
            medication = Medication.objects.create(
                item_seq=item_seq,
                item_name=item_name,
                entp_name=entp_name,
                item_image=item_image,
                class_name=class_name,
                dosage_form=dosage_form,
                is_prescription=is_prescription
            )
            medications.append(medication)
        self.stdout.write(f"✅ 의약품 등록: {len(medications)}개")

        # 6. 의약품-성분 관계
        for i, (medication, ingredient) in enumerate(zip(medications, ingredients)):
            MedicationIngredient.objects.create(
                medication=medication,
                ingredient=ingredient,
                content_amount=ingredient.main_ingr_density,
                content_unit=ingredient.main_ingr_unit,
                is_active_ingredient=True
            )
        self.stdout.write(f"✅ 의약품-성분 관계 등록: {len(medications)}개")

        # 7. 처방전 생성 (3개월간 월 1회 방문)
        prescriptions = []
        for i in range(3):
            prescription_date = start_date + timedelta(days=30 * i)
            prescription_id = f"PRESC_{prescription_date.strftime('%Y%m%d')}_001"
            prev_presc = prescriptions[-1] if prescriptions else None

            prescription = Prescription.objects.create(
                prescription_id=prescription_id,
                prescription_date=prescription_date.date(),
                previous_prescription=prev_presc,
                is_active=True
            )
            prescriptions.append(prescription)
        self.stdout.write(f"✅ 처방전 생성: {len(prescriptions)}개")

        # 8. 사용자 의료정보 생성
        medical_infos = []
        for i, prescription in enumerate(prescriptions):
            for j, illness in enumerate(illnesses):
                medical_info = UserMedicalInfo.objects.create(
                    user=user,
                    hospital=hospital,
                    illness=illness,
                    prescription=prescription,
                    is_primary=(j == 0)
                )
                medical_infos.append(medical_info)
        self.stdout.write(f"✅ 의료정보 생성: {len(medical_infos)}개")

        # 9. 처방전별 약물 정보 (용량 변화 반영)
        prescription_medications = []

        # 처방 패턴 정의
        prescription_patterns = [
            # 1차 처방 (3개월전)
            [
                (medications[0], {"morning": 1, "frequency": "daily"}, 30, 30, 30.0),  # 콘서타
                (medications[1], {"morning": 1, "evening": 1, "frequency": "daily"}, 60, 30, 60.0),  # 데파코트
                (medications[3], {"as_needed": True, "max_daily": 2, "frequency": "prn"}, 15, 30, 15.0)  # 자낙스
            ],
            # 2차 처방 (2개월전) - 퀘티아핀 추가
            [
                (medications[0], {"morning": 1, "frequency": "daily"}, 30, 30, 30.0),
                (medications[1], {"morning": 1, "evening": 1, "frequency": "daily"}, 60, 30, 60.0),
                (medications[2], {"evening": 1, "frequency": "daily"}, 30, 30, 30.0),  # 쎄로켈 추가
                (medications[3], {"as_needed": True, "max_daily": 3, "frequency": "prn"}, 30, 30, 30.0)  # 자낙스 증량
            ],
            # 3차 처방 (1개월전) - 자낙스 더 증량
            [
                (medications[0], {"morning": 1, "frequency": "daily"}, 30, 30, 30.0),
                (medications[1], {"morning": 1, "evening": 1, "frequency": "daily"}, 60, 30, 60.0),
                (medications[2], {"evening": 1, "frequency": "daily"}, 30, 30, 30.0),
                (medications[3], {"as_needed": True, "max_daily": 4, "frequency": "prn"}, 45, 30, 45.0)  # 자낙스 더 증량
            ]
        ]

        for i, (prescription, pattern) in enumerate(zip(prescriptions, prescription_patterns)):
            for medication, dosage_pattern, total_qty, duration, total_amount in pattern:
                presc_med = PrescriptionMedication.objects.create(
                    prescription=prescription,
                    medication=medication,
                    standard_dosage_pattern=dosage_pattern,
                    cycle_total_quantity=total_qty,
                    duration_days=duration,
                    total_quantity=total_amount
                )
                prescription_medications.append(presc_med)
        self.stdout.write(f"✅ 처방약물 등록: {len(prescription_medications)}개")

        # 10. 복약 그룹 및 주기 생성
        for i, (prescription, presc_date) in enumerate(
                zip(prescriptions, [start_date + timedelta(days=30 * j) for j in range(3)])):
            group = MedicationGroup.objects.create(
                group_id=f"GROUP_{prescription.prescription_id}",
                medical_info=medical_infos[i * 3],  # 첫 번째 의료정보 사용
                prescription=prescription,
                group_name=f"{presc_date.strftime('%Y년 %m월')} 처방",
                reminder_enabled=True
            )

            # 복약 주기
            cycle_start = presc_date.date()
            cycle_end = cycle_start + timedelta(days=30)

            cycle = MedicationCycle.objects.create(
                group=group,
                cycle_number=i + 1,
                cycle_start=cycle_start,
                cycle_end=cycle_end,
                is_active=(i == len(prescriptions) - 1)
            )

            # 해당 주기의 처방약물들에 대한 상세정보 생성
            cycle_prescription_meds = [pm for pm in prescription_medications if pm.prescription == prescription]

            for presc_med in cycle_prescription_meds:
                # 실제 복약 패턴
                actual_pattern = {"adherence_rate": random.uniform(0.7, 0.95)}
                remaining_qty = random.randint(0, 25)

                # 자낙스 PRN 특별 처리
                if "자낙스" in presc_med.medication.item_name:
                    remaining_qty = random.randint(5, 25)
                    patient_adjustments = {"prn_usage": "불안 증상 시에만 복용", "notes": "간헐적 복용"}
                else:
                    patient_adjustments = {"notes": "정기 복용"}

                detail = MedicationDetail.objects.create(
                    cycle=cycle,
                    prescription_medication=presc_med,
                    actual_dosage_pattern=actual_pattern,
                    remaining_quantity=remaining_qty,
                    patient_adjustments=patient_adjustments
                )

                # 복용 기록 생성
                self.create_medication_records(detail, cycle_start, cycle_end, actual_pattern, presc_med)

                # 알림 설정
                self.create_medication_alerts(detail, presc_med)

        self.stdout.write(self.style.SUCCESS('✅ 정신과 환자 더미데이터 생성 완료!'))
        self.stdout.write(f"📅 기간: {start_date.strftime('%Y-%m-%d')} ~ {current_date.strftime('%Y-%m-%d')}")
        self.stdout.write("👤 환자: ADHD + 양극성장애 + 불안장애")
        self.stdout.write("💊 처방약물: 콘서타, 데파코트, 쎄로켈, 자낙스(PRN)")

    def create_medication_records(self, detail, cycle_start, cycle_end, actual_pattern, presc_med):
        """복용 기록 생성"""
        record_date = cycle_start
        current_date = timezone.now().date()

        while record_date <= min(cycle_end, current_date):
            # 복용 여부 결정 (순응도 기반)
            if random.random() < actual_pattern["adherence_rate"]:
                record_type = "TAKEN"

                # 자낙스 PRN의 경우 특별 처리
                if "자낙스" in presc_med.medication.item_name:
                    if random.random() < 0.3:  # 30% 확률로만 복용
                        quantity = random.choice([0.25, 0.5, 0.75])
                        notes = f"불안 증상으로 인한 복용 ({quantity}mg)"
                    else:
                        record_date += timedelta(days=1)
                        continue
                else:
                    quantity = 1.0
                    notes = "정시 복용"
            else:
                record_type = "MISSED"
                quantity = 0.0
                notes = "복용 누락"

            MedicationRecord.objects.create(
                medication_detail=detail,
                record_type=record_type,
                record_date=timezone.make_aware(
                    datetime.combine(record_date, datetime.min.time().replace(hour=random.randint(7, 22)))
                ),
                quantity_taken=quantity,
                notes=notes
            )

            record_date += timedelta(days=1)

    def create_medication_alerts(self, detail, presc_med):
        """복약 알림 생성"""
        # 자낙스는 PRN이므로 알림 다르게 설정
        if "자낙스" in presc_med.medication.item_name:
            MedicationAlert.objects.create(
                medication_detail=detail,
                alert_type="PRN_REMINDER",
                alert_time="12:00:00",
                is_active=True,
                message="필요시 복용약이 있습니다"
            )
        else:
            # 정기 복용약 알림
            dosage_pattern = presc_med.standard_dosage_pattern
            if dosage_pattern.get("morning"):
                MedicationAlert.objects.create(
                    medication_detail=detail,
                    alert_type="MORNING",
                    alert_time="08:00:00",
                    is_active=True,
                    message="아침 약 복용 시간입니다"
                )
            if dosage_pattern.get("evening"):
                MedicationAlert.objects.create(
                    medication_detail=detail,
                    alert_type="EVENING",
                    alert_time="20:00:00",
                    is_active=True,
                    message="저녁 약 복용 시간입니다"
                )

    def clear_existing_data(self):
        """기존 데이터 삭제"""
        models_to_clear = [
            MedicationAlert, MedicationRecord, MedicationDetail,
            MedicationCycle, MedicationGroup, PrescriptionMedication,
            UserMedicalInfo, Prescription, MedicationIngredient,
            Medication, MainIngredient, Illness, Hospital, AyakUser
        ]

        for model in models_to_clear:
            count = model.objects.count()
            model.objects.all().delete()
            self.stdout.write(f"🗑️ {model.__name__}: {count}개 삭제")