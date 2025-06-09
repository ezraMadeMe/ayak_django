#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
식약처 의약품 정보 API를 통해 정신건강의학과 약물 정보를 수집하여 Medication 테이블을 채우는 스크립트

API 문서: https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService06/getDrugPrdtPrmsnDtlInq05

사용법:
python populate_medication.py --api-key YOUR_API_KEY
"""

import os
import sys
import django
import requests
import xml.etree.ElementTree as ET
import logging
import time
from datetime import datetime, date
from decimal import Decimal

# SSL 경고 억제 및 설정
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')
django.setup()

from user.models import Medication
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('medication_import.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MedicationImporter:
    """의약품 정보 API 임포터 클래스"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService06/getDrugPrdtPrmsnDtlInq05"

        # requests 세션 설정
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self.stats = {
            'total_ingredients': 0,
            'successful_ingredients': 0,
            'failed_ingredients': 0,
            'total_medications_found': 0,
            'medications_created': 0,
            'medications_updated': 0,
            'errors': 0
        }
        self.error_details = []

        # 정신건강의학과 약물 성분명 리스트 (한글)
        self.medication_ingredients = [
            # SSRI 항우울제
            '플루옥세틴', '파록세틴', '세르트랄린', '에스시탈로프람', '플루복사민',
            # SNRI 항우울제
            '벤라팍신', '둘록세틴', '밀나시프란', '데스벤라팍신',
            # 기타 항우울제
            '미르타자핀', '부프로피온', '트라조돈', '아고멜라틴', '보르티옥세틴', '티아넵틴', '레복세틴',
            # 삼환계 항우울제
            '아미트리프틸린', '이미프라민', '클로미프라민', '노르트리프틸린', '데시프라민', '독세핀', '마프로틸린',
            # MAOI
            '트라닐시프로민', '페넬진', '모클로베마이드', '셀레질린',
            # 비정형 항정신병약물
            '아리피프라졸', '쿠에티아핀', '올란자핀', '리스페리돈', '지프라시돈', '루라시돈', '팔리페리돈',
            '아세나핀', '브렉스피프라졸', '카리프라진', '클로티아핀', '설피라이드', '아미설프라이드',
            '페로스피론', '블로난세린', '조테핀', '록사핀',
            # 전형적 항정신병약물
            '할로페리돌', '클로르프로마진', '페르페나진', '티오틱센', '트리플루오페라진', '플루페나진',
            '레보메프로마진', '티오프로파제이트',
            # 기분안정제
            '탄산리튬', '발프로산', '카르바마제핀', '옥스카르바제핀', '라모트리진', '토피라메이트',
            # 벤조디아제핀 항불안제
            '알프라졸람', '로라제팜', '디아제팜', '클로나제팜', '브로마제팜', '에티졸람', '니트라제팜',
            '트리아졸람', '미다졸람', '테마제팜', '플루라제팜', '에스타졸람', '클로르디아제폭사이드',
            '로르메타제팜', '옥사제팜', '클로바잠',
            # 기타 항불안제
            '부스피론', '메프로바메이트',
            # 수면제
            '졸피뎀', '에스조피클론', '라멜테온', '수보렉산트',
            # ADHD 치료제
            '메틸페니데이트', '아토목세틴', '덱스메틸페니데이트', '리스덱삼페타민', '구안파신', '클로니딘',
            # 기타 정신과 약물
            '프로프라놀롤', '프레가발린', '멜라토닌', '덱스메데토미딘', '티아가빈', '비가바트린',
            '레베티라세탐', '가바펜틴', '페노바르비탈', '페람파넬', '칸나비디올', '펜플루라민',
            '아데메티오닌', '날트렉손'
        ]

        logger.info(f"총 {len(self.medication_ingredients)}개 성분명으로 의약품 검색 예정")

    def get_medication_data(self, item_name, page_no=1, num_of_rows=100):
        """API에서 의약품 데이터 가져오기"""
        params = {
            'serviceKey': self.api_key,
            'pageNo': str(page_no),
            'numOfRows': str(num_of_rows),
            'item_name': item_name,
            'type': 'xml'
        }

        try:
            logger.info(f"API 호출 - 성분명: {item_name}, 페이지: {page_no}")
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=30,
                verify=False
            )

            logger.debug(f"응답 상태: {response.status_code}")
            logger.debug(f"실제 요청 URL: {response.url}")

            response.raise_for_status()
            return self.parse_xml_response(response.text, item_name)

        except requests.exceptions.RequestException as e:
            logger.error(f"API 호출 실패 ({item_name}): {e}")
            return None, 0, f"API 호출 실패: {e}"
        except Exception as e:
            logger.error(f"데이터 처리 실패 ({item_name}): {e}")
            return None, 0, f"데이터 처리 실패: {e}"

    def parse_xml_response(self, xml_text, item_name):
        """XML 응답 파싱"""
        try:
            root = ET.fromstring(xml_text)

            # 결과 코드 확인
            result_code = root.find('.//resultCode')
            if result_code is not None and result_code.text != '00':
                result_msg = root.find('.//resultMsg')
                error_msg = result_msg.text if result_msg is not None else "알 수 없는 오류"
                logger.warning(f"API 경고 ({item_name}): {result_code.text} - {error_msg}")
                return [], 0, None

            # 총 개수 확인
            total_count_elem = root.find('.//totalCount')
            total_count = int(total_count_elem.text) if total_count_elem is not None else 0

            # 의약품 데이터 추출
            medications = []
            items = root.findall('.//item')

            for item in items:
                medication_data = self.extract_medication_data(item, item_name)
                if medication_data:
                    medications.append(medication_data)

            return medications, total_count, None

        except ET.ParseError as e:
            logger.error(f"XML 파싱 오류 ({item_name}): {e}")
            return None, 0, f"XML 파싱 오류: {e}"
        except Exception as e:
            logger.error(f"응답 처리 오류 ({item_name}): {e}")
            return None, 0, f"응답 처리 오류: {e}"

    def extract_medication_data(self, item, search_ingredient):
        """XML item에서 의약품 데이터 추출"""
        try:
            def get_text(element_name, default=''):
                elem = item.find(element_name)
                return elem.text.strip() if elem is not None and elem.text else default

            def get_decimal(element_name, default=None):
                try:
                    value = get_text(element_name)
                    if value and value.replace('.', '').replace(',', '').isdigit():
                        return Decimal(value.replace(',', ''))
                    return default
                except:
                    return default

            # 의약품 기본 정보
            medication_data = {
                'item_seq': get_text('ITEM_SEQ'),
                'item_name': get_text('ITEM_NAME'),
                'entp_name': get_text('ENTP_NAME'),  # 업체명
                'item_permit_date': get_text('ITEM_PERMIT_DATE'),  # 허가일자
                'cnsgn_manuf': get_text('CNSGN_MANUF'),  # 위탁제조업체
                'etc_otc_code': get_text('ETC_OTC_CODE'),  # 전문/일반 구분
                'item_image': get_text('ITEM_IMAGE'),  # 의약품 이미지
                'main_item_ingr': get_text('MAIN_ITEM_INGR'),  # 주성분
                'main_ingr_eng': get_text('MAIN_INGR_ENG'),  # 주성분 영문
                'chart': get_text('CHART'),  # 성상
                'material_name': get_text('MATERIAL_NAME'),  # 원료성분
                'ee_doc_data': get_text('EE_DOC_DATA'),  # 효능효과
                'ud_doc_data': get_text('UD_DOC_DATA'),  # 용법용량
                'nb_doc_data': get_text('NB_DOC_DATA'),  # 주의사항경고
                'insert_file': get_text('INSERT_FILE'),  # 첨부문서
                'storage_method': get_text('STORAGE_METHOD'),  # 저장방법
                'valid_term': get_text('VALID_TERM'),  # 유효기간
                'reexam_target': get_text('REEXAM_TARGET'),  # 재심사대상
                'reexam_date': get_text('REEXAM_DATE'),  # 재심사기간
                'pack_unit': get_text('PACK_UNIT'),  # 포장단위
                'edi_code': get_text('EDI_CODE'),  # 보험코드
                'permit_kind_code': get_text('PERMIT_KIND_CODE'),  # 허가종류
                'cancel_date': get_text('CANCEL_DATE'),  # 취소일자
                'cancel_name': get_text('CANCEL_NAME'),  # 취소사유
                'change_date': get_text('CHANGE_DATE'),  # 변경일자
                'narcotic_kind_code': get_text('NARCOTIC_KIND_CODE'),  # 마약종류코드
                'newdrug_class_code': get_text('NEWDRUG_CLASS_CODE'),  # 신약코드
                'induty_type': get_text('INDUTY_TYPE'),  # 업종구분
                'item_ingr_name': get_text('ITEM_INGR_NAME'),  # 주성분명
                'item_ingr_cnt': get_text('ITEM_INGR_CNT'),  # 주성분수
                'big_prdt_img_url': get_text('BIG_PRDT_IMG_URL'),  # 큰제품이미지
                'permit_date': get_text('PERMIT_DATE'),  # 허가일자
                'total_content': get_text('TOTAL_CONTENT'),  # 전체내용량
                'approval_no': get_text('APPROVAL_NO'),  # 허가번호
                'search_ingredient': search_ingredient  # 검색에 사용된 성분명
            }

            # 필수 필드 검증
            if not medication_data['item_name']:
                logger.warning(f"제품명이 없는 데이터 스킵 (검색성분: {search_ingredient})")
                return None

            return medication_data

        except Exception as e:
            logger.error(f"의약품 데이터 추출 오류 (검색성분: {search_ingredient}): {e}")
            return None

    def create_or_update_medication(self, medication_data):
        """의약품 정보 생성 또는 업데이트"""
        try:
            # 의약품 ID 생성 (제품명 + 업체명 기반)
            # medication_id = f"{medication_data['item_name']}_{medication_data['entp_name']}"
            # medication_id = medication_id.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')[:200]

            # 취소일자가 있으면 비활성화
            is_active = not bool(medication_data.get('cancel_date'))

            medication, created = Medication.objects.update_or_create(
                medication_id=medication_data['item_seq'],
                defaults={
                    'medication_name': medication_data['item_name'],
                    'main_item_ingr': medication_data['main_item_ingr'],
                    'main_ingr_eng': medication_data['main_ingr_eng'],
                    # 'dosage_form': medication_data.get('chart', ''),
                    # 'strength': medication_data.get('material_name', ''),
                    'manufacturer': medication_data.get('entp_name', ''),
                    # 'active_ingredient': medication_data.get('search_ingredient', ''),

                    # 식약처 API 추가 정보
                    # 'entp_name': medication_data.get('entp_name', ''),
                    # 'item_permit_date': medication_data.get('item_permit_date', ''),
                    # 'etc_otc_code': medication_data.get('etc_otc_code', ''),
                    'item_image': medication_data.get('item_image', ''),

                    # 의약품 상세 정보
                    # 'material_name': medication_data.get('material_name', ''),
                    # 'ee_doc_data': medication_data.get('ee_doc_data', ''),
                    # 'ud_doc_data': medication_data.get('ud_doc_data', ''),
                    # 'nb_doc_data': medication_data.get('nb_doc_data', ''),
                    # 'storage_method': medication_data.get('storage_method', ''),
                    # 'valid_term': medication_data.get('valid_term', ''),
                    # 'pack_unit': medication_data.get('pack_unit', ''),

                    # 보험 및 허가 정보
                    # 'edi_code': medication_data.get('edi_code', ''),
                    # 'approval_no': medication_data.get('approval_no', ''),
                    # 'permit_kind_code': medication_data.get('permit_kind_code', ''),
                    # 'narcotic_kind_code': medication_data.get('narcotic_kind_code', ''),

                    # 기타 정보
                    # 'total_content': medication_data.get('total_content', ''),
                    # 'big_prdt_img_url': medication_data.get('big_prdt_img_url', ''),
                    # 'insert_file': medication_data.get('insert_file', ''),

                    # 검색 및 상태 관리
                    # 'search_ingredient': medication_data.get('search_ingredient', ''),
                    # 'is_active': is_active,
                    # 'cancel_date': medication_data.get('cancel_date', ''),
                    # 'cancel_name': medication_data.get('cancel_name', ''),
                }
            )

            if created:
                self.stats['medications_created'] += 1
                logger.debug(f"✓ 생성: {medication_data['item_name']} ({medication_data['entp_name']})")
                return 'created'
            else:
                self.stats['medications_updated'] += 1
                logger.debug(f"↻ 업데이트: {medication_data['item_name']} ({medication_data['entp_name']})")
                return 'updated'

        except (IntegrityError, ValidationError) as e:
            self.stats['errors'] += 1
            error_msg = f"DB 저장 오류 - 제품명: {medication_data['item_name']}, 오류: {str(e)}"
            self.error_details.append(error_msg)
            logger.error(error_msg)
            return 'error'
        except Exception as e:
            self.stats['errors'] += 1
            error_msg = f"예상치 못한 오류 - 제품명: {medication_data['item_name']}, 오류: {str(e)}"
            self.error_details.append(error_msg)
            logger.error(error_msg)
            return 'error'

    def import_medications_by_ingredient(self, ingredient, batch_size=100, delay_seconds=1):
        """특정 성분명으로 의약품 정보 임포트"""
        logger.info(f"🔍 '{ingredient}' 성분 의약품 검색 시작")

        try:
            # 첫 번째 호출로 총 개수 확인
            medications, total_count, error = self.get_medication_data(
                item_name=ingredient,
                page_no=1,
                num_of_rows=batch_size
            )

            if error:
                logger.error(f"'{ingredient}' 성분 검색 실패: {error}")
                self.stats['failed_ingredients'] += 1
                return False

            if total_count == 0:
                logger.info(f"'{ingredient}' 성분으로 등록된 의약품이 없습니다.")
                self.stats['successful_ingredients'] += 1
                return True

            logger.info(f"'{ingredient}' 성분: 총 {total_count}개 의약품 발견")
            self.stats['total_medications_found'] += total_count

            # 첫 번째 배치 처리
            if medications:
                self.process_batch(medications)

            # 나머지 페이지 처리
            if total_count > batch_size:
                total_pages = (total_count + batch_size - 1) // batch_size

                for page_no in range(2, total_pages + 1):
                    logger.debug(f"'{ingredient}' 성분: {page_no}/{total_pages} 페이지 처리 중...")

                    # API 호출 제한을 위한 딜레이
                    time.sleep(delay_seconds)

                    medications, _, error = self.get_medication_data(
                        item_name=ingredient,
                        page_no=page_no,
                        num_of_rows=batch_size
                    )

                    if error:
                        logger.error(f"'{ingredient}' 성분 페이지 {page_no} 호출 실패: {error}")
                        continue

                    if medications:
                        self.process_batch(medications)

            self.stats['successful_ingredients'] += 1
            logger.info(f"✅ '{ingredient}' 성분 검색 완료")
            return True

        except Exception as e:
            logger.error(f"'{ingredient}' 성분 처리 중 예외 발생: {e}")
            self.stats['failed_ingredients'] += 1
            return False

    def process_batch(self, medications):
        """배치 단위로 의약품 데이터 처리"""
        try:
            with transaction.atomic():
                for medication_data in medications:
                    result = self.create_or_update_medication(medication_data)

                    if result in ['created', 'updated']:
                        logger.debug(f"{result}: {medication_data['item_name']} ({medication_data['entp_name']})")

        except Exception as e:
            logger.error(f"배치 처리 중 오류: {e}")
            self.stats['errors'] += len(medications)

    def import_all_medications(self, batch_size=100, delay_seconds=1, specific_ingredients=None):
        """모든 성분명으로 의약품 정보 임포트"""
        logger.info("정신건강의학과 의약품 정보 임포트 시작")

        # 특정 성분만 지정된 경우
        if specific_ingredients:
            ingredients_to_search = [ing for ing in specific_ingredients if ing in self.medication_ingredients]
            logger.info(f"지정된 성분만 검색: {ingredients_to_search}")
        else:
            ingredients_to_search = self.medication_ingredients

        self.stats['total_ingredients'] = len(ingredients_to_search)

        for i, ingredient in enumerate(ingredients_to_search, 1):
            logger.info(f"📋 진행률: {i}/{len(ingredients_to_search)} ({(i / len(ingredients_to_search) * 100):.1f}%)")

            success = self.import_medications_by_ingredient(
                ingredient=ingredient,
                batch_size=batch_size,
                delay_seconds=delay_seconds
            )

            # 성분 간 딜레이
            if i < len(ingredients_to_search):
                time.sleep(delay_seconds)

        logger.info("모든 의약품 정보 임포트 완료")

    def print_summary(self):
        """처리 결과 요약 출력"""
        logger.info("=" * 50)
        logger.info("의약품 정보 임포트 완료")
        logger.info("=" * 50)
        logger.info(f"총 검색 성분: {self.stats['total_ingredients']}개")
        logger.info(f"성공한 성분: {self.stats['successful_ingredients']}개")
        logger.info(f"실패한 성분: {self.stats['failed_ingredients']}개")
        logger.info(f"발견된 의약품: {self.stats['total_medications_found']:,}개")
        logger.info(f"생성된 의약품: {self.stats['medications_created']:,}개")
        logger.info(f"업데이트된 의약품: {self.stats['medications_updated']:,}개")
        logger.info(f"오류 발생: {self.stats['errors']:,}개")

        if self.error_details:
            logger.info(f"\n주요 오류 내용 (총 {len(self.error_details)}개 중 최대 10개):")
            for error in self.error_details[:10]:
                logger.info(f"  - {error}")

        # 성공률 계산
        if self.stats['total_ingredients'] > 0:
            success_rate = (self.stats['successful_ingredients'] / self.stats['total_ingredients']) * 100
            logger.info(f"\n성분 검색 성공률: {success_rate:.2f}%")

        # 최종 데이터 수 확인
        try:
            total_medications = Medication.objects.count()
            logger.info(f"\n현재 저장된 총 의약품 데이터: {total_medications:,}개")
        except Exception as e:
            logger.warning(f"총 데이터 수 확인 실패: {e}")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='정신건강의학과 의약품 정보 임포트 스크립트')
    parser.add_argument('--api-key', type=str, required=True, help='공공데이터포털 API 키')
    parser.add_argument('--batch-size', type=int, default=100, help='배치 크기 (최대 1000)')
    parser.add_argument('--delay', type=float, default=1.0, help='API 호출 간 딜레이(초)')
    parser.add_argument('--ingredients', type=str, nargs='+', help='특정 성분만 검색 (예: Fluoxetine Sertraline)')

    args = parser.parse_args()

    # API 키 검증
    if not args.api_key or len(args.api_key) < 10:
        logger.error("올바른 API 키를 입력해주세요.")
        sys.exit(1)

    # 배치 크기 제한
    if args.batch_size > 1000:
        logger.warning("배치 크기를 1000으로 제한합니다.")
        args.batch_size = 1000

    # 임포터 생성
    importer = MedicationImporter(args.api_key)

    # 기존 데이터 수 확인
    existing_count = Medication.objects.count()
    logger.info(f"기존 의약품 데이터 수: {existing_count:,}")

    # 데이터 임포트 실행
    try:
        importer.import_all_medications(
            batch_size=args.batch_size,
            delay_seconds=args.delay,
            specific_ingredients=args.ingredients
        )

        # 결과 요약 출력
        importer.print_summary()

        # 최종 데이터 수 확인
        final_count = Medication.objects.count()
        logger.info(f"최종 의약품 데이터 수: {final_count:,}")
        logger.info(f"증가한 데이터 수: {final_count - existing_count:,}")

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
        importer.print_summary()
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# 사용 예시:
"""
# 모든 정신건강의학과 성분명으로 검색
python common/scripts/populate_medication.py --api-key YOUR_API_KEY

# 특정 성분만 검색
python populate_medication.py --api-key YOUR_API_KEY --ingredients Fluoxetine Sertraline Quetiapine

# 배치 크기와 딜레이 조정
python populate_medication.py --api-key YOUR_API_KEY --batch-size 50 --delay 2

# 몇 개 성분으로 테스트
python populate_medication.py --api-key YOUR_API_KEY --ingredients Fluoxetine Paroxetine --delay 0.5
"""