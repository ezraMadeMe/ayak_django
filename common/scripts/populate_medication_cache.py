import os
import sys
import django
import requests
import time
import json
from datetime import datetime
from urllib.parse import urlencode, quote
import xml.etree.ElementTree as ET

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')
django.setup()

from django.db import transaction
from user.models.main_ingredient import MainIngredient
from user.models import Medication  # 실제 앱 이름으로 변경


class MedicationAPICollector:
    def __init__(self, service_key):
        self.service_key = service_key
        self.base_url = "http://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService06/getDrugPrdtPrmsnDtlInq05"
        self.collected_count = 0
        self.target_count = 5000
        self.delay = 0.1  # API 호출 간격 (초)

    def get_medication_data(self, page_no=1, num_of_rows=100):
        """의약품 정보 API 호출"""
        params = {
            'serviceKey': self.service_key,
            'pageNo': page_no,
            'numOfRows': num_of_rows,
            'type': 'xml'
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"API 호출 오류 (페이지 {page_no}): {e}")
            return None

    def parse_xml_response(self, xml_data):
        """XML 응답 데이터 파싱"""
        try:
            root = ET.fromstring(xml_data)
            items = []

            # 응답 구조에 따라 경로 조정 필요
            for item in root.findall('.//item'):
                medication_data = {}

                # 의약품 정보 추출
                medication_data['item_seq'] = item.findtext('ITEM_SEQ', '')
                medication_data['item_name'] = item.findtext('ITEM_NAME', '')
                medication_data['entp_name'] = item.findtext('ENTP_NAME', '')
                medication_data['item_permit_date'] = item.findtext('ITEM_PERMIT_DATE', '')
                medication_data['main_ingr_eng'] = item.findtext('MAIN_INGR_ENG', '')  # 영문 주성분명
                medication_data['item_image'] = item.findtext('ITEM_IMAGE', '')
                medication_data['big_prdt_type_name'] = item.findtext('BIG_PRDT_TYPE_NAME', '')
                medication_data['prdt_type_name'] = item.findtext('PRDT_TYPE_NAME', '')
                medication_data['permit_kind_name'] = item.findtext('PERMIT_KIND_NAME', '')
                medication_data['cancel_date'] = item.findtext('CANCEL_DATE', '')
                medication_data['cancel_name'] = item.findtext('CANCEL_NAME', '')

                if medication_data['item_seq'] and medication_data['item_name']:
                    items.append(medication_data)

            return items
        except ET.ParseError as e:
            print(f"XML 파싱 오류: {e}")
            return []

    def extract_main_ingredients(self, ingr_string):
        """주성분 문자열에서 성분명 추출 (사용하지 않음 - 삭제 예정)"""
        # 이 메서드는 더 이상 사용하지 않음
        # API의 MAIN_INGR_ENG를 직접 사용하여 MainIngredient와 매칭
        pass

    def find_matching_main_ingredient(self, main_ingr_eng):
        """API의 MAIN_INGR_ENG와 완전히 일치하는 MainIngredient 찾기"""
        if not main_ingr_eng or not main_ingr_eng.strip():
            return None

        try:
            # main_ingr_name_en 컬럼에 API의 MAIN_INGR_ENG 문자열이 전체가 포함되어 있는지 확인
            # 대소문자 구분 없이 검색하고, 공백 제거 후 비교
            clean_main_ingr_eng = main_ingr_eng.strip()

            matching_ingredients = MainIngredient.objects.filter(
                main_ingr_name_en__icontains=clean_main_ingr_eng,
                is_active=True
            )

            # 정확한 일치 확인 (전체 문자열이 포함되어야 함)
            for ingredient in matching_ingredients:
                if clean_main_ingr_eng.lower() in ingredient.main_ingr_name_en.lower():
                    return ingredient

            return None
        except Exception as e:
            print(f"주성분 매칭 오류 ({main_ingr_eng}): {e}")
            return None

    def save_medication_data(self, medication_data):
        """의약품 데이터를 데이터베이스에 저장"""
        try:
            with transaction.atomic():
                # 의약품 정보 저장
                medication, created = Medication.objects.update_or_create(
                    medication_id=int(medication_data['item_seq']),
                    defaults={
                        'medication_name': medication_data['item_name'][:200],
                        'manufacturer': medication_data['entp_name'][:100],
                    }
                )

                # 기존 주성분 관계 초기화 (업데이트 시)
                if not created:
                    medication.main_ingredients.clear()

                # 이미지 URL이 있으면 저장 (실제 구현시 이미지 다운로드 로직 추가 필요)
                if medication_data.get('item_image'):
                    # medication.item_image = medication_data['item_image']
                    # medication.save()
                    pass

                # 주성분 처리 - API의 MAIN_INGR_ENG 사용
                if medication_data.get('main_ingr_eng'):
                    main_ingr_eng = medication_data['main_ingr_eng'].strip()

                    # MainIngredient에서 일치하는 성분 찾기
                    matching_ingredient = self.find_matching_main_ingredient(main_ingr_eng)

                    if matching_ingredient:
                        medication.main_ingredients.add(matching_ingredient)
                        print(f"  → 주성분 매칭 성공: {matching_ingredient.display_name}")
                    else:
                        print(f"  → 주성분 매칭 실패: '{main_ingr_eng}' - 매칭되는 성분 없음")
                else:
                    print(f"  → 주성분 정보 없음")

                if created:
                    self.collected_count += 1
                    print(f"저장완료 ({self.collected_count}/5000): {medication.medication_name}")

                return True
        except Exception as e:
            print(f"데이터 저장 오류: {e}")
            print(f"문제 데이터: {medication_data}")
            return False

    def collect_all_data(self):
        """전체 데이터 수집"""
        print("의약품 데이터 수집을 시작합니다...")
        page = 1
        num_of_rows = 100
        consecutive_empty_pages = 0
        max_empty_pages = 5

        while self.collected_count < self.target_count and consecutive_empty_pages < max_empty_pages:
            print(f"\n페이지 {page} 처리 중... (수집된 데이터: {self.collected_count}개)")

            # API 호출
            xml_data = self.get_medication_data(page, num_of_rows)
            if not xml_data:
                consecutive_empty_pages += 1
                page += 1
                continue

            # 데이터 파싱
            items = self.parse_xml_response(xml_data)
            if not items:
                consecutive_empty_pages += 1
                page += 1
                continue

            consecutive_empty_pages = 0  # 데이터가 있으면 초기화

            # 데이터 저장
            saved_count = 0
            for item_data in items:
                if self.collected_count >= self.target_count:
                    break

                if self.save_medication_data(item_data):
                    saved_count += 1

            print(f"페이지 {page}: {saved_count}개 저장됨")

            # API 호출 제한 대응
            time.sleep(self.delay)
            page += 1

            # 진행률 출력
            progress = (self.collected_count / self.target_count) * 100
            print(f"진행률: {progress:.1f}% ({self.collected_count}/{self.target_count})")

        print(f"\n데이터 수집 완료! 총 {self.collected_count}개의 의약품 정보가 저장되었습니다.")


def create_sample_data():
    """샘플 데이터 생성 (API 키가 없을 경우)"""
    sample_medications = [
        {
            'item_seq': '200001001',
            'item_name': '타이레놀정 500mg',
            'entp_name': '한국얀센',
            'main_ingr_eng': 'Acetaminophen',
            'item_image': ''
        },
        {
            'item_seq': '200001002',
            'item_name': '애드빌정 200mg',
            'entp_name': '화이자제약',
            'main_ingr_eng': 'Ibuprofen',
            'item_image': ''
        },
        {
            'item_seq': '200001003',
            'item_name': '낙센정 220mg',
            'entp_name': '동아제약',
            'main_ingr_eng': 'Naproxen',
            'item_image': ''
        },
        {
            'item_seq': '200001004',
            'item_name': '판콜에스정',
            'entp_name': '동화약품',
            'main_ingr_eng': 'Acetaminophen;Chlorpheniramine Maleate;Dextromethorphan HBr',
            'item_image': ''
        },
        {
            'item_seq': '200001005',
            'item_name': '훼스탈정',
            'entp_name': '한독',
            'main_ingr_eng': 'Diastase;Pancreatin',
            'item_image': ''
        },
        {
            'item_seq': '200001006',
            'item_name': '지르텍정 10mg',
            'entp_name': 'UCB코리아',
            'main_ingr_eng': 'Cetirizine HCl',
            'item_image': ''
        },
        {
            'item_seq': '200001007',
            'item_name': '클라리틴정 10mg',
            'entp_name': 'MSD',
            'main_ingr_eng': 'Loratadine',
            'item_image': ''
        },
        {
            'item_seq': '200001008',
            'item_name': '오그멘틴정 625mg',
            'entp_name': 'GSK',
            'main_ingr_eng': 'Amoxicillin;Clavulanic acid',
            'item_image': ''
        },
        {
            'item_seq': '200001009',
            'item_name': '라식스정 40mg',
            'entp_name': '한독',
            'main_ingr_eng': 'Furosemide',
            'item_image': ''
        },
        {
            'item_seq': '200001010',
            'item_name': '메트포르민정 500mg',
            'entp_name': '동아제약',
            'main_ingr_eng': 'Metformin HCl',
            'item_image': ''
        }
        # ... 더 많은 샘플 데이터 추가 가능
    ]

    collector = MedicationAPICollector('')
    for sample in sample_medications:
        collector.save_medication_data(sample)

    print(f"샘플 데이터 {len(sample_medications)}개가 저장되었습니다.")


def main():
    # 공공데이터포털에서 발급받은 서비스키 입력
    SERVICE_KEY = input("공공데이터포털 서비스키를 입력하세요 (샘플 데이터만 사용하려면 엔터): ").strip()

    if not SERVICE_KEY:
        print("샘플 데이터를 생성합니다...")
        create_sample_data()
        return

    # API 데이터 수집기 초기화
    collector = MedicationAPICollector(SERVICE_KEY)

    # 데이터 수집 실행
    try:
        collector.collect_all_data()
    except KeyboardInterrupt:
        print(f"\n사용자에 의해 중단되었습니다. 현재까지 {collector.collected_count}개 수집됨.")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")


if __name__ == "__main__":
    main()