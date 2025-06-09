#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
건강보험심사평가원 병원정보 API를 통해 HospitalCache 테이블을 채우는 스크립트

API 문서: https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15001698

사용법:
python populate_hospital_cache.py --api-key YOUR_API_KEY

2025-06-06 14:59:34,346 - INFO - 필터 적용된 종별코드: 01(상급종합병원), 11(종합병원), 21(병원)
2025-06-06 14:59:34,347 - INFO - 총 수신 데이터: 1,815
2025-06-06 14:59:34,347 - INFO - 필터링으로 제외: 8,085
2025-06-06 14:59:34,347 - INFO - 실제 처리 데이터: -6,270
2025-06-06 14:59:34,347 - INFO - 생성된 데이터: 1,715
2025-06-06 14:59:34,347 - INFO - 업데이트된 데이터: 100
2025-06-06 14:59:34,347 - INFO - 오류 발생: 0
2025-06-06 14:59:34,349 - INFO - 01(상급종합병원): 47개
2025-06-06 14:59:34,350 - INFO - 11(종합병원): 331개
2025-06-06 14:59:34,350 - INFO - 21(병원): 1,437개


"""

import os
import sys
import django
import requests
import xml.etree.ElementTree as ET
import logging
import time
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')
django.setup()

from user.models import HospitalCache
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hospital_import.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HospitalDataImporter:
    """병원정보 API 임포터 클래스"""

    def __init__(self, api_key, hospital_type_filters=None):
        self.api_key = api_key
        self.base_url = "http://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"

        # 종별코드 필터 설정 (기본값: 01,11,21 - 상급종합병원, 종합병원, 병원)
        self.hospital_type_filters = hospital_type_filters or ['01', '11', '21']

        # 종별코드 설명
        self.hospital_type_names = {
            '01': '상급종합병원',
            '11': '종합병원',
            '21': '병원',
            '28': '요양병원',
            '29': '정신병원',
            '31': '의원',
            '41': '치과병원',
            '42': '치과의원',
            '51': '한방병원',
            '52': '한방의원',
            '61': '부속의원',
            '71': '보건소',
            '72': '보건지소',
            '73': '보건진료소',
            '74': '모자보건센터',
            '75': '보건의료원',
            '81': '조산원',
            '91': '종합병원급 약국',
            '92': '한방병원급 약국'
        }

        self.stats = {
            'total_requested': 0,
            'total_received': 0,
            'filtered_out': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        self.error_details = []

        logger.info(f"병원 종별코드 필터: {self.hospital_type_filters}")
        filter_names = [self.hospital_type_names.get(code, f'알수없음({code})') for code in self.hospital_type_filters]
        logger.info(f"수집 대상 병원 유형: {', '.join(filter_names)}")

    def get_hospital_data(self, page_no=1, num_of_rows=100, sido_cd=None, sggu_cd=None):
        """API에서 병원 데이터 가져오기"""
        params = {
            'serviceKey': self.api_key,
            'pageNo': page_no,
            'numOfRows': num_of_rows,
        }

        if sido_cd:
            params['sidoCd'] = sido_cd
        if sggu_cd:
            params['sgguCd'] = sggu_cd

        try:
            logger.info(f"API 호출 - 페이지: {page_no}, 행수: {num_of_rows}")
            response = requests.get(self.base_url, params=params, timeout=30)
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

            # 병원 데이터 추출
            hospitals = []
            items = root.findall('.//item')
            filtered_count = 0

            for item in items:
                hospital_data = self.extract_hospital_data(item)
                if hospital_data is None:
                    filtered_count += 1  # 필터링된 데이터 카운트
                    continue
                hospitals.append(hospital_data)

            # 필터링 통계 업데이트
            self.stats['filtered_out'] += filtered_count

            if filtered_count > 0:
                logger.debug(f"이번 배치에서 {filtered_count}개 병원이 종별코드 필터링으로 제외됨")

            return hospitals, total_count, None

        except ET.ParseError as e:
            logger.error(f"XML 파싱 오류: {e}")
            return None, 0, f"XML 파싱 오류: {e}"
        except Exception as e:
            logger.error(f"응답 처리 오류: {e}")
            return None, 0, f"응답 처리 오류: {e}"

    def extract_hospital_data(self, item):
        """XML item에서 병원 데이터 추출"""
        try:
            def get_text(element_name, default=''):
                elem = item.find(element_name)
                return elem.text.strip() if elem is not None and elem.text else default

            def get_int(element_name, default=0):
                try:
                    value = get_text(element_name, '0')
                    return int(value) if value.isdigit() else default
                except (ValueError, AttributeError):
                    return default

            def get_decimal(element_name, default=None):
                try:
                    value = get_text(element_name)
                    return Decimal(value) if value else default
                except (ValueError, InvalidOperation):
                    return default

            # 종별코드 확인 및 필터링
            hospital_type_code = get_text('clCd')
            if hospital_type_code not in self.hospital_type_filters:
                # 필터링된 병원 유형이므로 None 반환 (수집하지 않음)
                return None

            hospital_data = {
                'hospital_code': get_text('ykiho'),
                'hospital_name': get_text('yadmNm'),
                'hospital_phone': get_text('telno'),
                'hospital_type_code': hospital_type_code,
                'hospital_type_name': get_text('clCdNm'),
                'establishment_type_code': get_text('estbDd'),
                'establishment_type_name': get_text('estbDdNm'),
                'postal_code': get_text('postNo'),
                'address': get_text('addr'),
                'road_address': get_text('roadAddr'),
                'sido_code': get_text('sidoCd'),
                'sido_name': get_text('sidoCdNm'),
                'sigungu_code': get_text('sgguCd'),
                'sigungu_name': get_text('sgguCdNm'),
                'latitude': get_decimal('YPos'),
                'longitude': get_decimal('XPos'),
                'homepage_url': get_text('hospUrl'),
                'business_status_code': get_text('drTotCnt'),
                'total_doctors': get_int('drTotCnt'),
                'total_beds': get_int('sickBedCnt'),
            }

            # 필수 필드 검증
            if not hospital_data['hospital_code']:
                logger.warning("요양기관기호가 없는 데이터 스킵")
                return None

            return hospital_data

        except Exception as e:
            logger.error(f"병원 데이터 추출 오류: {e}")
            return None

    def create_or_update_hospital(self, hospital_data):
        """병원 정보 생성 또는 업데이트"""
        try:
            hospital, created = HospitalCache.objects.update_or_create(
                hospital_code=hospital_data['hospital_code'],
                defaults={
                    'hospital_name': hospital_data['hospital_name'],
                    'hospital_phone': hospital_data['hospital_phone'],
                    'hospital_type_code': hospital_data['hospital_type_code'],
                    'hospital_type_name': hospital_data['hospital_type_name'],
                    'establishment_type_code': hospital_data['establishment_type_code'],
                    'establishment_type_name': hospital_data['establishment_type_name'],
                    'postal_code': hospital_data['postal_code'],
                    'address': hospital_data['address'],
                    'road_address': hospital_data['road_address'],
                    'sido_code': hospital_data['sido_code'],
                    'sido_name': hospital_data['sido_name'],
                    'sigungu_code': hospital_data['sigungu_code'],
                    'sigungu_name': hospital_data['sigungu_name'],
                    'latitude': hospital_data['latitude'],
                    'longitude': hospital_data['longitude'],
                    'homepage_url': hospital_data['homepage_url'],
                    'total_doctors': hospital_data['total_doctors'],
                    'total_beds': hospital_data['total_beds'],
                    'data_reference_date': date.today(),
                    'is_active': True,
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
            error_msg = f"DB 저장 오류 - 병원코드: {hospital_data['hospital_code']}, 오류: {str(e)}"
            self.error_details.append(error_msg)
            logger.error(error_msg)
            return 'error'

    def import_all_hospitals(self, batch_size=100, delay_seconds=1, sido_codes=None):
        """모든 병원 정보 임포트"""
        logger.info("병원정보 API 임포트 시작")

        # 시도 코드가 지정되지 않으면 전국 데이터 수집
        if sido_codes is None:
            sido_codes = [None]  # 전국
        elif isinstance(sido_codes, str):
            sido_codes = [sido_codes]

        for sido_cd in sido_codes:
            logger.info(f"시도코드 {sido_cd} 데이터 수집 시작")

            # 첫 번째 호출로 총 개수 확인
            hospitals, total_count, error = self.get_hospital_data(
                page_no=1,
                num_of_rows=batch_size,
                sido_cd=sido_cd
            )

            if error:
                logger.error(f"시도코드 {sido_cd} 데이터 수집 실패: {error}")
                continue

            if not hospitals:
                logger.warning(f"시도코드 {sido_cd}에서 데이터를 찾을 수 없습니다.")
                continue

            logger.info(f"시도코드 {sido_cd}: 총 {total_count}개 병원 데이터 수집 예정")

            # 첫 번째 배치 처리
            self.process_batch(hospitals)

            # 나머지 페이지 처리
            total_pages = (total_count + batch_size - 1) // batch_size

            for page_no in range(2, total_pages + 1):
                logger.info(f"시도코드 {sido_cd}: {page_no}/{total_pages} 페이지 처리 중...")

                # API 호출 제한을 위한 딜레이
                time.sleep(delay_seconds)

                hospitals, _, error = self.get_hospital_data(
                    page_no=page_no,
                    num_of_rows=batch_size,
                    sido_cd=sido_cd
                )

                if error:
                    logger.error(f"페이지 {page_no} 호출 실패: {error}")
                    continue

                if hospitals:
                    self.process_batch(hospitals)

                # 진행상황 로깅
                if page_no % 10 == 0:
                    progress = (page_no / total_pages) * 100
                    logger.info(f"시도코드 {sido_cd} 진행률: {progress:.1f}%")

        logger.info("모든 병원정보 임포트 완료")

    def process_batch(self, hospitals):
        """배치 단위로 병원 데이터 처리"""
        try:
            with transaction.atomic():
                for hospital_data in hospitals:
                    self.stats['total_received'] += 1
                    result = self.create_or_update_hospital(hospital_data)

                    if result in ['created', 'updated']:
                        logger.debug(f"{result}: {hospital_data['hospital_code']} - {hospital_data['hospital_name']}")

        except Exception as e:
            logger.error(f"배치 처리 중 오류: {e}")
            self.stats['errors'] += len(hospitals)

    def print_summary(self):
        """처리 결과 요약 출력"""
        logger.info("=" * 50)
        logger.info("병원정보 임포트 완료")
        logger.info("=" * 50)

        # 종별코드 필터 정보 출력
        filter_names = [f"{code}({self.hospital_type_names.get(code, '알수없음')})" for code in self.hospital_type_filters]
        logger.info(f"필터 적용된 종별코드: {', '.join(filter_names)}")

        logger.info(f"총 수신 데이터: {self.stats['total_received']:,}")
        logger.info(f"필터링으로 제외: {self.stats['filtered_out']:,}")
        logger.info(f"실제 처리 데이터: {self.stats['total_received'] - self.stats['filtered_out']:,}")
        logger.info(f"생성된 데이터: {self.stats['created']:,}")
        logger.info(f"업데이트된 데이터: {self.stats['updated']:,}")
        logger.info(f"오류 발생: {self.stats['errors']:,}")

        if self.error_details:
            logger.info(f"\n주요 오류 내용 (총 {len(self.error_details)}개 중 최대 10개):")
            for error in self.error_details[:10]:
                logger.info(f"  - {error}")

        # 성공률 계산 (필터링 제외된 데이터 기준)
        processed_count = self.stats['total_received'] - self.stats['filtered_out']
        if processed_count > 0:
            success_rate = (self.stats['created'] + self.stats['updated']) / processed_count * 100
            logger.info(f"\n성공률: {success_rate:.2f}% (필터링 제외된 데이터 기준)")

        # 종별코드별 통계 (가능한 경우)
        try:
            for code in self.hospital_type_filters:
                count = HospitalCache.objects.filter(hospital_type_code=code).count()
                type_name = self.hospital_type_names.get(code, '알수없음')
                logger.info(f"{code}({type_name}): {count:,}개")
        except Exception as e:
            logger.warning(f"종별코드별 통계 계산 실패: {e}")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='병원정보 API 임포트 스크립트')
    parser.add_argument('--api-key', type=str, required=True, help='공공데이터포털 API 키')
    parser.add_argument('--batch-size', type=int, default=100, help='배치 크기 (최대 1000)')
    parser.add_argument('--delay', type=float, default=1.0, help='API 호출 간 딜레이(초)')
    parser.add_argument('--sido-codes', type=str, nargs='+', help='특정 시도코드만 수집 (예: 11 26 27)')
    parser.add_argument('--hospital-types', type=str, nargs='+',
                        default=['01', '11', '21'],
                        help='수집할 종별코드 (기본값: 01 11 21 - 상급종합병원, 종합병원, 병원)')

    args = parser.parse_args()

    # API 키 검증
    if not args.api_key or len(args.api_key) < 10:
        logger.error("올바른 API 키를 입력해주세요.")
        sys.exit(1)

    # 배치 크기 제한
    if args.batch_size > 1000:
        logger.warning("배치 크기를 1000으로 제한합니다.")
        args.batch_size = 1000

    # 임포터 생성 (종별코드 필터 포함)
    importer = HospitalDataImporter(args.api_key, args.hospital_types)

    # 기존 데이터 수 확인
    existing_count = HospitalCache.objects.count()
    logger.info(f"기존 병원 데이터 수: {existing_count:,}")

    # 데이터 임포트 실행
    try:
        importer.import_all_hospitals(
            batch_size=args.batch_size,
            delay_seconds=args.delay,
            sido_codes=args.sido_codes
        )

        # 결과 요약 출력
        importer.print_summary()

        # 최종 데이터 수 확인
        final_count = HospitalCache.objects.count()
        logger.info(f"최종 병원 데이터 수: {final_count:,}")
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
# 기본 실행 (상급종합병원, 종합병원, 병원만 수집)
python common/scripts/populate_hospital_cache.py --api-key YOUR_API_KEY

# 상급종합병원만 수집
python populate_hospital_cache.py --api-key YOUR_API_KEY --hospital-types 01

# 종합병원과 병원만 수집
python populate_hospital_cache.py --api-key YOUR_API_KEY --hospital-types 11 21

# 모든 의료기관 수집 (의원, 치과 등 포함)
python populate_hospital_cache.py --api-key YOUR_API_KEY --hospital-types 01 11 21 31 41 42 51 52

# 서울지역 상급종합병원과 종합병원만
python populate_hospital_cache.py --api-key YOUR_API_KEY --sido-codes 11 --hospital-types 01 11

# 배치 크기와 딜레이 조정
python populate_hospital_cache.py --api-key YOUR_API_KEY --hospital-types 01 11 21 --batch-size 50 --delay 2
"""