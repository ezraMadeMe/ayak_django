import os
import sys
import django
import requests
import xml.etree.ElementTree as ET
import logging
import time
import re
from datetime import datetime, date
from decimal import Decimal

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')
django.setup()

from user.models import DiseaseCache
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('disease_import.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DiseaseDataImporter:
    """질병정보 API 임포터 클래스"""

    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://apis.data.go.kr/B551182/diseaseInfoService1/getDissNameCodeList1"
        self.stats = {
            'total_requested': 0,
            'total_received': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'search_letters_completed': 0,
            'search_letters_failed': 0
        }
        self.error_details = []

        # A-Z 검색용 알파벳 리스트
        self.search_letters = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        logger.info(f"A-Z 검색 모드: {len(self.search_letters)}개 알파벳으로 전체 검색 수행")

    def get_disease_data(self, page_no=1, num_of_rows=100, search_text=None):
        """API에서 질병 데이터 가져오기"""
        params = {
            'serviceKey': self.api_key,
            'pageNo': page_no,
            'numOfRows': num_of_rows,
            'sickType': '2',  # 고정값
            'medTp': '1',  # 고정값
            'diseaseType': 'SICK_CD',  # 고정값
            'searchText' : search_text
        }

        try:
            logger.info(f"API 호출 - 페이지: {page_no}, 행수: {num_of_rows}, 검색텍스트: {search_text}")
            response = requests.get(self.base_url, params=params, timeout=30)
            logger.info(f"API 호출 - 페이지: {response.url}")
            response.raise_for_status()

            return self.parse_xml_response(response.text)

        except requests.exceptions.RequestException as e:
            logger.error(f"API 호출 실패: {e}")
            return None, 0, None
        except Exception as e:
            logger.error(f"데이터 처리 실패: {e}")
            return None, 0, None

    def parse_xml_response(self, xml_text):
        """XML 응답 파싱"""
        try:
            root = ET.fromstring(xml_text)

            # 결과 코드 확인
            result_code = root.find('.//resultCode')
            if result_code is not None and result_code.text != '00':
                result_msg = root.find('.//resultMsg')
                error_msg = result_msg.text if result_msg is not None else "알 수 없는 오류"
                logger.error(f"API 오류: {result_code.text} - {error_msg}")
                return None, 0, error_msg

            # 총 개수 확인
            total_count_elem = root.find('.//totalCount')
            total_count = int(total_count_elem.text) if total_count_elem is not None else 0

            # 질병 데이터 추출
            diseases = []
            items = root.findall('.//item')

            for item in items:
                disease_data = self.extract_disease_data(item)
                if disease_data:
                    diseases.append(disease_data)

            return diseases, total_count, None

        except ET.ParseError as e:
            logger.error(f"XML 파싱 오류: {e}")
            return None, 0, f"XML 파싱 오류: {e}"
        except Exception as e:
            logger.error(f"응답 처리 오류: {e}")
            return None, 0, f"응답 처리 오류: {e}"

    def extract_disease_data(self, item):
        """XML item에서 질병 데이터 추출"""
        try:
            def get_text(element_name, default=''):
                elem = item.find(element_name)
                return elem.text.strip() if elem is not None and elem.text else default

            disease_name_kr = get_text('sickNm')
            disease_name_en = get_text('sickEngNm')
            disease_code = get_text('sickCd')

            disease_data = {
                'disease_code': disease_code,
                'disease_name_kr': disease_name_kr,
                'disease_name_en': disease_name_en,
            }

            # 필수 필드 검증
            if not disease_data['disease_code'] or not disease_data['disease_name_kr']:
                logger.warning("질병코드 또는 질병명이 없는 데이터 스킵")
                return None

            return disease_data

        except Exception as e:
            logger.error(f"질병 데이터 추출 오류: {e}")
            return None

    def create_or_update_disease(self, disease_data):
        """질병 정보 생성 또는 업데이트"""
        try:
            disease, created = DiseaseCache.objects.update_or_create(
                disease_code=disease_data['disease_code'],
                defaults={
                    'disease_name_kr': disease_data['disease_name_kr'],
                    'disease_name_en': disease_data['disease_name_en'],
                }
            )

            if created:
                self.stats['created'] += 1
                return 'created'
            else:
                self.stats['updated'] += 1
                return 'updated'

        except (IntegrityError, ValidationError) as e:
            self.stats['errors'] += 1
            error_msg = f"DB 저장 오류 - 질병코드: {disease_data['disease_code']}, 오류: {str(e)}"
            self.error_details.append(error_msg)
            logger.error(error_msg)
            return 'error'

    def import_all_diseases(self, batch_size=100, delay_seconds=1):
        """A-Z 검색으로 모든 질병 정보 임포트"""
        logger.info("질병정보 A-Z 전체 검색 임포트 시작")

        successful_letters = []
        failed_letters = []

        for letter in self.search_letters:
            logger.info(f"🔍 '{letter}' 알파벳 검색 시작")

            try:
                # 첫 번째 호출로 총 개수 확인
                diseases, total_count, error = self.get_disease_data(
                    page_no=1,
                    num_of_rows=batch_size,
                    search_text=letter
                )

                if error:
                    logger.error(f"'{letter}' 알파벳 검색 실패: {error}")
                    failed_letters.append(letter)
                    self.stats['search_letters_failed'] += 1
                    continue

                if not diseases and total_count == 0:
                    logger.info(f"'{letter}' 알파벳에서 데이터를 찾을 수 없습니다.")
                    successful_letters.append(letter)
                    self.stats['search_letters_completed'] += 1
                    continue

                logger.info(f"'{letter}' 알파벳: 총 {total_count}개 질병 데이터 수집 예정")

                # 첫 번째 배치 처리
                if diseases:
                    self.process_batch(diseases)

                # 나머지 페이지 처리
                if total_count > batch_size:
                    total_pages = (total_count + batch_size - 1) // batch_size

                    for page_no in range(2, total_pages + 1):
                        logger.debug(f"'{letter}' 알파벳: {page_no}/{total_pages} 페이지 처리 중...")

                        # API 호출 제한을 위한 딜레이
                        time.sleep(delay_seconds)

                        diseases, _, error = self.get_disease_data(
                            page_no=page_no,
                            num_of_rows=batch_size,
                            search_text=letter
                        )

                        if error:
                            logger.error(f"'{letter}' 알파벳 페이지 {page_no} 호출 실패: {error}")
                            continue

                        if diseases:
                            self.process_batch(diseases)

                        # 진행상황 로깅 (10페이지마다)
                        if page_no % 10 == 0:
                            progress = (page_no / total_pages) * 100
                            logger.debug(f"'{letter}' 알파벳 진행률: {progress:.1f}%")

                successful_letters.append(letter)
                self.stats['search_letters_completed'] += 1
                logger.info(f"✅ '{letter}' 알파벳 검색 완료 ({total_count}개)")

                # 알파벳 간 딜레이
                time.sleep(delay_seconds)

            except Exception as e:
                logger.error(f"'{letter}' 알파벳 처리 중 예외 발생: {e}")
                failed_letters.append(letter)
                self.stats['search_letters_failed'] += 1
                continue

        # 최종 결과 출력
        logger.info("=" * 50)
        logger.info("A-Z 검색 완료")
        logger.info("=" * 50)
        logger.info(f"성공한 알파벳: {', '.join(successful_letters)} ({len(successful_letters)}개)")
        if failed_letters:
            logger.warning(f"실패한 알파벳: {', '.join(failed_letters)} ({len(failed_letters)}개)")
        logger.info("모든 질병정보 임포트 완료")

    def process_batch(self, diseases):
        """배치 단위로 질병 데이터 처리"""
        try:
            with transaction.atomic():
                for disease_data in diseases:
                    self.stats['total_received'] += 1
                    result = self.create_or_update_disease(disease_data)

                    if result in ['created', 'updated']:
                        logger.debug(f"{result}: {disease_data['disease_code']} - {disease_data['disease_name_kr']}")

        except Exception as e:
            logger.error(f"배치 처리 중 오류: {e}")
            self.stats['errors'] += len(diseases)

    def print_summary(self):
        """처리 결과 요약 출력"""
        logger.info("=" * 50)
        logger.info("질병정보 임포트 완료")
        logger.info("=" * 50)
        logger.info(f"A-Z 검색 완료: {self.stats['search_letters_completed']}/{len(self.search_letters)}개 알파벳")
        logger.info(f"검색 실패: {self.stats['search_letters_failed']}개 알파벳")
        logger.info(f"총 수신 데이터: {self.stats['total_received']:,}")
        logger.info(f"생성된 데이터: {self.stats['created']:,}")
        logger.info(f"업데이트된 데이터: {self.stats['updated']:,}")
        logger.info(f"오류 발생: {self.stats['errors']:,}")

        if self.error_details:
            logger.info(f"\n주요 오류 내용 (총 {len(self.error_details)}개 중 최대 10개):")
            for error in self.error_details[:10]:
                logger.info(f"  - {error}")

        # 성공률 계산
        if self.stats['total_received'] > 0:
            success_rate = (self.stats['created'] + self.stats['updated']) / self.stats['total_received'] * 100
            logger.info(f"\n성공률: {success_rate:.2f}%")

        # 알파벳별 성공률
        if len(self.search_letters) > 0:
            alphabet_success_rate = (self.stats['search_letters_completed'] / len(self.search_letters)) * 100
            logger.info(f"알파벳 검색 성공률: {alphabet_success_rate:.2f}%")

        # 최종 데이터 수 확인
        try:
            total_diseases = DiseaseCache.objects.count()
            logger.info(f"\n현재 저장된 총 질병 데이터: {total_diseases:,}개")
        except Exception as e:
            logger.warning(f"총 데이터 수 확인 실패: {e}")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='질병정보 API 임포트 스크립트')
    parser.add_argument('--api-key', type=str, required=True, help='공공데이터포털 API 키')
    parser.add_argument('--batch-size', type=int, default=100, help='배치 크기 (최대 1000)')
    parser.add_argument('--delay', type=float, default=1.0, help='API 호출 간 딜레이(초)')
    parser.add_argument('--keywords', type=str, nargs='+', help='특정 검색 키워드만 수집')
    parser.add_argument('--full-import', action='store_true', help='전체 데이터 수집 (키워드 없이)')
    parser.add_argument('--letters', type=str, nargs='+', help='특정 알파벳만 검색 (예: A B C)')
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
    importer = DiseaseDataImporter(args.api_key)

    # 기존 데이터 수 확인
    existing_count = DiseaseCache.objects.count()
    logger.info(f"기존 질병 데이터 수: {existing_count:,}")


    # 특정 알파벳만 검색하는 경우
    if args.letters:
        # 대문자로 변환하고 중복 제거
        specified_letters = list(set([letter.upper() for letter in args.letters if letter.isalpha()]))
        importer.search_letters = sorted(specified_letters)
        logger.info(f"지정된 알파벳만 검색: {importer.search_letters}")

    # 기존 데이터 수 확인
    existing_count = DiseaseCache.objects.count()
    logger.info(f"기존 질병 데이터 수: {existing_count:,}")

    # 데이터 임포트 실행
    try:
        importer.import_all_diseases(
            batch_size=args.batch_size,
            delay_seconds=args.delay
        )

        # 결과 요약 출력
        importer.print_summary()

        # 최종 데이터 수 확인
        final_count = DiseaseCache.objects.count()
        logger.info(f"최종 질병 데이터 수: {final_count:,}")
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
# 전체 질병 데이터 수집
python populate_disease_cache.py --api-key YOUR_API_KEY --full-import

# 특정 키워드로 수집
python populate_disease_cache.py --api-key YOUR_API_KEY --keywords 당뇨 고혈압 심장병

# 기본 키워드로 수집 (감염, 만성, 심장, 뇌, 폐, 간, 신장, 당뇨, 고혈압)
python populate_disease_cache.py --api-key YOUR_API_KEY

# 배치 크기와 딜레이 조정
python populate_disease_cache.py --api-key YOUR_API_KEY --batch-size 50 --delay 2
"""

# 사용 예시:
"""
# A-Z 전체 검색 (기본)
python common/scripts/populate_disease_cache.py --api-key YOUR_API_KEY

# 특정 알파벳만 검색
python populate_disease_cache.py --api-key YOUR_API_KEY --letters A B C

# 배치 크기와 딜레이 조정
python populate_disease_cache.py --api-key YOUR_API_KEY --batch-size 50 --delay 2

# A, M, Z 알파벳만 테스트
python populate_disease_cache.py --api-key YOUR_API_KEY --letters A M Z --delay 0.5
"""  # !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
건강보험심사평가원 질병정보 API를 통해 DiseaseCache 테이블을 채우는 스크립트

API 문서: https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15119055

사용법:
python populate_disease_cache.py --api-key YOUR_API_KEY
"""
