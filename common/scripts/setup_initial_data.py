import os
import sqlite3
import json
from datetime import datetime, date, timedelta
import random
import uuid


# SQLite datetime 어댑터 설정 (Python 3.12 호환)
def adapt_datetime(dt):
    return dt.isoformat()


def convert_datetime(s):
    return datetime.fromisoformat(s.decode())


def adapt_date(d):
    return d.isoformat()


def convert_date(s):
    return date.fromisoformat(s.decode())


# SQLite 어댑터 등록
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_converter("date", convert_date)

DB_PATH = '../../db.sqlite3'

# 데이터베이스 연결
def create_connection():
    if not os.path.exists(DB_PATH):
        print(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {DB_PATH}")
        print("Django 프로젝트 루트 디렉토리에서 실행하거나 DB_PATH를 수정해주세요.")
        return None

    conn = sqlite3.connect(DB_PATH)
    return conn

def get_table_info(conn, table_name):
    """테이블의 컬럼 정보 확인"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [col[1] for col in columns]  # 컬럼명만 반환


def check_tables_exist(conn):
    """필요한 테이블들이 존재하는지 확인"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [table[0] for table in cursor.fetchall()]

    # Django 테이블명 (앱명_모델명 형태)
    required_tables = [
        'ayak_users',
        'hospitals',
        'illnesses',
        'main_ingredients',
        'medications',
        'medication_ingredients',
        'prescriptions',
        'user_medical_info',
        'prescription_medications',
        'medication_groups',
        'medication_cycles',
        'medication_details',
        'medication_records',
        'medication_alerts'
    ]

    print("📋 기존 테이블 목록:")
    for table in existing_tables:
        print(f"  - {table}")

    print("\n🔍 필요한 테이블 확인:")
    for table in required_tables:
        if any(table.lower() in existing.lower() for existing in existing_tables):
            print(f"  ✅ {table} (유사 테이블 존재)")
        else:
            print(f"  ❌ {table} (없음)")

    # 실제 존재하는 테이블명 찾기 (대소문자 무관)
    actual_tables = {}
    for req_table in required_tables:
        model_name = req_table.split('_')[-1]  # 마지막 부분이 모델명
        for existing in existing_tables:
            if model_name.lower() in existing.lower():
                actual_tables[model_name] = existing
                break

    return actual_tables


def insert_dummy_data():
    conn = create_connection()
    if not conn:
        return

    cursor = conn.cursor()

    # 테이블 존재 확인 및 실제 테이블명 매핑
    table_mapping = check_tables_exist(conn)

    if not table_mapping:
        print("❌ 필요한 테이블을 찾을 수 없습니다.")
        print("Django 모델이 마이그레이션되었는지 확인해주세요: python manage.py migrate")
        return

    print(f"\n🔄 {len(table_mapping)}개 테이블에 데이터 삽입 시작...")

    # 현재 날짜 기준으로 3개월 전부터 데이터 생성
    current_date = datetime.now()
    start_date = current_date - timedelta(days=90)

    try:
        # 1. 사용자 데이터
        if 'ayakusers' in table_mapping:
            user_table = table_mapping['ayakusers']
            user_columns = get_table_info(conn, user_table)
            print(f"📝 {user_table} 컬럼: {user_columns}")

            # Django는 보통 id가 자동증가
            user_data = {
                'user_id': 'USR_PSYCH_001',
                'user_name': '김정신',
                'join_date': (start_date - timedelta(days=30)).isoformat(),
                'push_agree': 1,
                'is_active': 1,
                'created_at': current_date.isoformat(),
                'updated_at': current_date.isoformat()
            }

            # 존재하는 컬럼만 사용
            filtered_data = {k: v for k, v in user_data.items() if k in user_columns}
            columns = ', '.join(filtered_data.keys())
            placeholders = ', '.join(['?' for _ in filtered_data])

            cursor.execute(f'''
                INSERT INTO {user_table} ({columns}) VALUES ({placeholders})
                ''', list(filtered_data.values()))

            # user_pk = cursor.lastrowid
            user_pk = "1234123"
            print(f"✅ 사용자 생성 (ID: {user_pk})")

        # 2. 병원 데이터
        if 'hospitals' in table_mapping:
            hospital_table = table_mapping['hospitals']
            hospital_data = {
                'hospital_id': 'HOSP_001',
                'user_id': user_pk if 'user_id' in get_table_info(conn, hospital_table) else 'USR_PSYCH_001',
                'hosp_code': 'PSYCH001',
                'hosp_name': '삼성공감정신건강의학과왕십리점',
                'hosp_type': '의원',
                'doctor_name': '이정현',
                'address': '서울특별시 종로구 대학로 101',
                'phone_number': '02-2072-2972',
                'created_at': current_date.isoformat(),
                'updated_at': current_date.isoformat()
            }

            hospital_columns = get_table_info(conn, hospital_table)
            filtered_data = {k: v for k, v in hospital_data.items() if k in hospital_columns}
            columns = ', '.join(filtered_data.keys())
            placeholders = ', '.join(['?' for _ in filtered_data])

            cursor.execute(f'''
                INSERT INTO {hospital_table} ({columns}) VALUES ({placeholders})
                ''', list(filtered_data.values()))

            hospital_pk = cursor.lastrowid
            print(f"✅ 병원 생성 (ID: {hospital_pk})")

        # 3. 질병 데이터
        illness_pks = []
        if 'illnesses' in table_mapping:
            illness_table = table_mapping['illnesses']
            illnesses_data = [
                ('ILL_ADHD_001', 'DISEASE', '주의력결핍 과잉행동장애', 'F90.0', start_date - timedelta(days=365)),
                ('ILL_BIPOLAR_001', 'DISEASE', '양극성 정동장애', 'F31.9', start_date - timedelta(days=180)),
                ('ILL_ANXIETY_001', 'DISEASE', '일반화불안장애', 'F41.1', start_date - timedelta(days=90))
            ]

            illness_columns = get_table_info(conn, illness_table)

            for ill_id, ill_type, ill_name, ill_code, ill_start in illnesses_data:
                illness_data = {
                    'illness_id': ill_id,
                    'user_id': user_pk if 'user_id' in illness_columns else 'USR_PSYCH_001',
                    'ill_type': ill_type,
                    'ill_name': ill_name,
                    'ill_code': ill_code,
                    'ill_start': ill_start.date().isoformat(),
                    'ill_end': None,
                    'is_chronic': 1,
                    'created_at': current_date.isoformat(),
                    'updated_at': current_date.isoformat()
                }

                filtered_data = {k: v for k, v in illness_data.items() if k in illness_columns}
                columns = ', '.join(filtered_data.keys())
                placeholders = ', '.join(['?' for _ in filtered_data])

                cursor.execute(f'''
                    INSERT INTO {illness_table} ({columns}) VALUES ({placeholders})
                    ''', list(filtered_data.values()))

                illness_pks.append(cursor.lastrowid)

            print(f"✅ 질병 생성: {len(illness_pks)}개")

        # 4. 주성분 데이터
        ingredient_pks = []
        if 'mainIngredients' in table_mapping:
            ingredient_table = table_mapping['mainIngredients']
            ingredients_data = [
                ('INGR_METHYLPHENIDATE', 'METH001', 'TAB', '정제', '메틸페니데이트염산염', 'Methylphenidate HCl', 1117, '경구', 18.0,
                 'mg'),
                ('INGR_VALPROATE', 'VALP001', 'TAB', '서방정', '발프로산나트륨', 'Sodium Valproate', 1143, '경구', 500.0, 'mg'),
                ('INGR_QUETIAPINE', 'QUET001', 'TAB', '서방정', '퀘티아핀푸마르산염', 'Quetiapine Fumarate', 1171, '경구', 200.0,
                 'mg'),
                ('INGR_ALPRAZOLAM', 'ALPR001', 'TAB', '정제', '알프라졸람', 'Alprazolam', 1124, '경구', 0.25, 'mg')
            ]

            ingredient_columns = get_table_info(conn, ingredient_table)

            for ingr_code, orig_code, dosage_form_code, dosage_form, name_kr, name_en, class_code, route, density, unit in ingredients_data:
                ingredient_data = {
                    'ingr_code': ingr_code,
                    'original_code': orig_code,
                    'dosage_form_code': dosage_form_code,
                    'dosage_form': dosage_form,
                    'main_ingr_name_kr': name_kr,
                    'main_ingr_name_en': name_en,
                    'classification_code': class_code,
                    'administration_route': route,
                    'main_ingr_density': density,
                    'main_ingr_unit': unit,
                    'original_density_text': f"{density}{unit}",
                    'is_combination': 0,
                    'combination_group': None,
                    'is_active': 1,
                    'notes': '정신과 약물',
                    'data_quality_score': 95,
                    'created_at': current_date.isoformat(),
                    'updated_at': current_date.isoformat()
                }

                filtered_data = {k: v for k, v in ingredient_data.items() if k in ingredient_columns}
                columns = ', '.join(filtered_data.keys())
                placeholders = ', '.join(['?' for _ in filtered_data])

                cursor.execute(f'''
                    INSERT INTO {ingredient_table} ({columns}) VALUES ({placeholders})
                    ''', list(filtered_data.values()))

                ingredient_pks.append(cursor.lastrowid)

            print(f"✅ 주성분 생성: {len(ingredient_pks)}개")

        # 5. 의약품 데이터
        medication_pks = []
        if 'medications' in table_mapping:
            medication_table = table_mapping['medications']
            medications_data = [
                (200001, '콘서타서방정18밀리그램', '한국얀센', 'concerta_18mg.jpg', '중추신경계용약', '서방정', True),
                (200002, '데파코트서방정500밀리그램', '한국애브비', 'depakote_500mg.jpg', '항전간제', '서방정', True),
                (200003, '쎄로켈서방정200밀리그램', '한국아스트라제네카', 'seroquel_200mg.jpg', '항정신병약', '서방정', True),
                (200004, '자낙스정0.25밀리그램', '한국화이자', 'xanax_025mg.jpg', '항불안제', '정제', True)
            ]

            medication_columns = get_table_info(conn, medication_table)

            for item_seq, item_name, entp_name, item_image, class_name, dosage_form, is_prescription in medications_data:
                medication_data = {
                    'item_seq': item_seq,
                    'item_name': item_name,
                    'entp_name': entp_name,
                    'item_image': item_image,
                    'class_name': class_name,
                    'dosage_form': dosage_form,
                    'is_prescription': 1 if is_prescription else 0,
                    'created_at': current_date.isoformat(),
                    'updated_at': current_date.isoformat()
                }

                filtered_data = {k: v for k, v in medication_data.items() if k in medication_columns}
                columns = ', '.join(filtered_data.keys())
                placeholders = ', '.join(['?' for _ in filtered_data])

                cursor.execute(f'''
                    INSERT INTO {medication_table} ({columns}) VALUES ({placeholders})
                    ''', list(filtered_data.values()))

                medication_pks.append(cursor.lastrowid)

            print(f"✅ 의약품 생성: {len(medication_pks)}개")

        # 6. 처방전 데이터
        prescriptions = []
        if 'prescriptions' in table_mapping:
            prescription_table = table_mapping['prescriptions']
            prescription_columns = get_table_info(conn, prescription_table)

            for i in range(3):
                prescription_date = start_date + timedelta(days=30 * i)
                prescription_id = f"PRESC_{prescription_date.strftime('%Y%m%d')}_001"
                prev_presc_id = prescriptions[-1] if prescriptions else None

                prescription = {
                    'prescription_id': prescription_id,
                    'prescription_date': prescription_date.date().isoformat(),
                    'previous_prescription_id': prev_presc_id,
                    'is_active': 1,
                    'created_at': current_date.isoformat(),
                    'updated_at': current_date.isoformat()
                }

                filtered_data = {k: v for k, v in prescription.items() if k in prescription_columns}
                columns = ', '.join(filtered_data.keys())
                placeholders = ', '.join(['?' for _ in filtered_data])

                cursor.execute(f'''
                    INSERT INTO {prescription_table} ({columns}) VALUES ({placeholders})
                    ''', list(filtered_data.values()))

                prescriptions.append(cursor.lastrowid)

            print(f"✅ 처방전 생성: {len(prescriptions)}개")

        # 7. 복용 기록 샘플 (간단히)
        if 'medicationrecords' in table_mapping:
            record_table = table_mapping['medicationrecords']
            record_columns = get_table_info(conn, record_table)

            # 최근 30일간 복용 기록 생성
            for i in range(30):
                record_date = (current_date - timedelta(days=i))

                record_data = {
                    'medication_detail_id': 1,  # 임시 값
                    'record_type': random.choice(['TAKEN', 'MISSED']),
                    'record_date': record_date.isoformat(),
                    'quantity_taken': random.choice([0, 0.25, 0.5, 1.0]),
                    'notes': '테스트 복용 기록',
                    'created_at': current_date.isoformat(),
                    'updated_at': current_date.isoformat()
                }

                filtered_data = {k: v for k, v in record_data.items() if k in record_columns}

                if filtered_data:  # 컬럼이 매치되는 경우만
                    columns = ', '.join(filtered_data.keys())
                    placeholders = ', '.join(['?' for _ in filtered_data])

                    try:
                        cursor.execute(f'''
                            INSERT INTO {record_table} ({columns}) VALUES ({placeholders})
                            ''', list(filtered_data.values()))
                    except sqlite3.Error as e:
                        print(f"⚠️ 복용 기록 삽입 오류 (무시): {e}")
                        break

                # 8. 사용자 의료정보 생성
                medical_info_ids = []
                for i, (prescription_id, _) in enumerate(prescriptions):
                    for j, illness_id in enumerate(["ILL_ADHD_001", "ILL_BIPOLAR_001", "ILL_ANXIETY_001"]):
                        med_info_id = i * 3 + j + 1
                        cursor.execute('''
                        INSERT INTO user_medical_info (id, user_id, hospital_id, illness_id, prescription_id, is_primary, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (med_info_id, 'USR_PSYCH_001', 'HOSP_001', illness_id, prescription_id, j == 0,
                              current_date,
                              current_date))
                        medical_info_ids.append(med_info_id)

                # 9. 처방전별 약물 정보 (용량 변화 반영)
                prescription_med_data = []

                # 1차 처방 (3개월전)
                presc1_meds = [
                    (prescriptions[0][0], 200001, {"morning": 1, "frequency": "daily"}, 30, 30, 30.0),
                    # 콘서타 18mg
                    (prescriptions[0][0], 200002, {"morning": 1, "evening": 1, "frequency": "daily"}, 60, 30,
                     60.0),
                    # 데파코트 500mg
                    (prescriptions[0][0], 200004, {"as_needed": True, "max_daily": 2, "frequency": "prn"}, 15,
                     30, 15.0)
                    # 자낙스 0.25mg PRN
                ]

                # 2차 처방 (2개월전) - 퀘티아핀 추가, 자낙스 증량
                presc2_meds = [
                    (prescriptions[1][0], 200001, {"morning": 1, "frequency": "daily"}, 30, 30, 30.0),
                    # 콘서타 18mg 유지
                    (prescriptions[1][0], 200002, {"morning": 1, "evening": 1, "frequency": "daily"}, 60, 30,
                     60.0),
                    # 데파코트 500mg 유지
                    (prescriptions[1][0], 200003, {"evening": 1, "frequency": "daily"}, 30, 30, 30.0),
                    # 쎄로켈 200mg 추가
                    (prescriptions[1][0], 200004, {"as_needed": True, "max_daily": 3, "frequency": "prn"}, 30,
                     30, 30.0)
                    # 자낙스 증량
                ]

                # 3차 처방 (1개월전) - 자낙스 더 증량
                presc3_meds = [
                    (prescriptions[2][0], 200001, {"morning": 1, "frequency": "daily"}, 30, 30, 30.0),
                    # 콘서타 18mg 유지
                    (prescriptions[2][0], 200002, {"morning": 1, "evening": 1, "frequency": "daily"}, 60, 30,
                     60.0),
                    # 데파코트 500mg 유지
                    (prescriptions[2][0], 200003, {"evening": 1, "frequency": "daily"}, 30, 30, 30.0),
                    # 쎄로켈 200mg 유지
                    (prescriptions[2][0], 200004, {"as_needed": True, "max_daily": 4, "frequency": "prn"}, 45,
                     30, 45.0)
                    # 자낙스 더 증량
                ]

                all_presc_meds = [presc1_meds, presc2_meds, presc3_meds]

                for presc_meds in all_presc_meds:
                    for presc_id, med_id, dosage_pattern, total_qty, duration, total_amount in presc_meds:
                        cursor.execute('''
                        INSERT INTO prescription_medications (prescription_id, medication_id, standard_dosage_pattern, cycle_total_quantity, duration_days, total_quantity, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (presc_id, med_id, json.dumps(dosage_pattern), total_qty, duration, total_amount,
                              current_date,
                              current_date))
                        prescription_med_data.append(cursor.lastrowid)

            # 10. 복약 그룹 생성
            group_data = []
            for i, (prescription_id, presc_date) in enumerate(prescriptions):
                group_id = f"GROUP_{prescription_id}"
                med_info_id = medical_info_ids[i * 3]  # 첫 번째 의료정보 ID 사용

                cursor.execute('''
                INSERT INTO medication_groups (group_id, medical_info_id, prescription_id, group_name, reminder_enabled, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (group_id, med_info_id, prescription_id, f"{presc_date.strftime('%Y년 %m월')} 처방", True,
                      current_date,
                      current_date))
                group_data.append((group_id, presc_date))

            # 11. 복약 주기 생성
            cycle_data = []
            for i, (group_id, presc_date) in enumerate(group_data):
                cycle_start = presc_date.date()
                cycle_end = cycle_start + timedelta(days=30)

                cursor.execute('''
                INSERT INTO medication_cycles (group_id, cycle_number, cycle_start, cycle_end, is_active, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (group_id, i + 1, cycle_start, cycle_end, i == len(group_data) - 1, current_date, current_date))
                cycle_data.append((cursor.lastrowid, cycle_start, cycle_end))

            # 12. 복약 상세 정보 및 복용 기록 생성
            detail_ids = []
            for cycle_idx, (cycle_id, cycle_start, cycle_end) in enumerate(cycle_data):
                # 해당 주기의 처방약물들
                start_idx = cycle_idx * (3 if cycle_idx == 0 else 4)  # 첫 처방은 3개, 이후는 4개
                end_idx = start_idx + (3 if cycle_idx == 0 else 4)

                for presc_med_idx in range(start_idx, min(end_idx, len(prescription_med_data))):
                    presc_med_id = prescription_med_data[presc_med_idx]

                    # 실제 복약 패턴 (환자 조정사항 포함)
                    actual_pattern = {"adherence_rate": random.uniform(0.7, 0.95)}
                    patient_adjustments = {"notes": "간헐적 복용 누락", "side_effects": []}

                    # 자낙스의 경우 PRN이므로 특별 처리
                    if (presc_med_idx - start_idx) == (2 if cycle_idx == 0 else 3):  # 자낙스 인덱스
                        remaining_qty = random.randint(5, 25)
                        patient_adjustments["prn_usage"] = "불안 증상 시에만 복용"
                    else:
                        remaining_qty = random.randint(0, 5)

                    cursor.execute('''
                    INSERT INTO medication_details (cycle_id, prescription_medication_id, actual_dosage_pattern, remaining_quantity, patient_adjustments, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (cycle_id, presc_med_id, json.dumps(actual_pattern), remaining_qty,
                          json.dumps(patient_adjustments), current_date, current_date))

                    detail_id = cursor.lastrowid
                    detail_ids.append(detail_id)

                    # 복용 기록 생성 (주기 동안의 기록들)
                    record_date = cycle_start
                    while record_date <= min(cycle_end, current_date.date()):
                        # 복용 여부 결정 (순응도 기반)
                        if random.random() < actual_pattern["adherence_rate"]:
                            record_type = "TAKEN"
                            # 자낙스 PRN의 경우
                            if (presc_med_idx - start_idx) == (2 if cycle_idx == 0 else 3):
                                # PRN은 매일 복용하지 않음
                                if random.random() < 0.3:  # 30% 확률로만 복용
                                    quantity = random.choice([0.25, 0.5, 0.75])  # 용량 조절
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

                        cursor.execute('''
                        INSERT INTO medication_records (medication_detail_id, record_type, record_date, quantity_taken, notes, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (detail_id, record_type,
                              datetime.combine(record_date, datetime.min.time().replace(hour=random.randint(7, 22))),
                              quantity, notes, current_date, current_date))

                        record_date += timedelta(days=1)

            # 13. 복약 알림 설정
            alert_times = [
                ("MORNING", "08:00:00", "아침 약 복용 시간입니다"),
                ("EVENING", "20:00:00", "저녁 약 복용 시간입니다"),
                ("PRN_REMINDER", "12:00:00", "필요시 복용약이 있습니다")
            ]

            for detail_id in detail_ids[-12:]:  # 최근 처방의 알림만 활성화
                for alert_type, alert_time, message in alert_times:
                    cursor.execute('''
                    INSERT INTO medication_alerts (medication_detail_id, alert_type, alert_time, is_active, message, created_at, updated_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (detail_id, alert_type, alert_time, True, message, current_date, current_date))

            print("✅ 복용 기록 샘플 생성")

        conn.commit()
        print(f"\n🎉 데이터 삽입 완료!")
        print(f"📊 Django Admin이나 API에서 확인 가능합니다.")

    except sqlite3.Error as e:
        print(f"❌ 데이터베이스 오류: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ 일반 오류: {e}")
        conn.rollback()
    finally:
        conn.close()

    print("✅ 정신과 환자 더미데이터 생성 완료!")
    print(f"📅 기간: {start_date.strftime('%Y-%m-%d')} ~ {current_date.strftime('%Y-%m-%d')}")
    print("👤 환자: ADHD + 양극성장애 + 불안장애")
    print("💊 처방약물:")
    print("   - 콘서타 18mg (ADHD)")
    print("   - 데파코트 500mg (양극성장애)")
    print("   - 쎄로켈 200mg (양극성장애, 2차 처방부터)")
    print("   - 자낙스 0.25mg PRN (불안장애, 용량 점진적 증량)")
    print("📊 생성된 기록:")
    print("   - 3회 처방전 (월 1회 방문)")
    print("   - 일일 복용 기록 (순응도 70-95%)")
    print("   - PRN 약물 사용 패턴")
    print("   - 용량 조정 이력")


def main():
    print("🏥 정신과 환자 더미데이터 생성을 시작합니다...")
    insert_dummy_data()


if __name__ == "__main__":
    main()