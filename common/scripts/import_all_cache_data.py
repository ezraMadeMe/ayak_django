# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
병원정보와 질병정보를 한 번에 임포트하는 통합 스크립트

사용법:
python import_all_cache_data.py --api-key YOUR_API_KEY
"""

import os
import sys
import django
import logging
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')
django.setup()

# 개별 임포터 클래스들 import
from populate_hospital_cache import HospitalDataImporter
from populate_disease_cache import DiseaseDataImporter
from user.models import HospitalCache, DiseaseCache

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_cache_import.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class UnifiedCacheImporter:
    """통합 캐시 데이터 임포터"""

    def __init__(self, api_key, hospital_type_filters=None):
        self.api_key = api_key
        self.hospital_importer = HospitalDataImporter(api_key, hospital_type_filters)
        self.disease_importer = DiseaseDataImporter(api_key)

        self.total_stats = {
            'start_time': None,
            'end_time': None,
            'hospital_stats': {},
            'disease_stats': {},
            'total_errors': 0
        }

    def import_hospital_data(self, batch_size=100, delay_seconds=1, sido_codes=None):
        """병원 데이터 임포트"""
        logger.info("🏥 병원정보 임포트 시작")

        try:
            existing_count = HospitalCache.objects.count()
            logger.info(f"기존 병원 데이터: {existing_count:,}개")

            self.hospital_importer.import_all_hospitals(
                batch_size=batch_size,
                delay_seconds=delay_seconds,
                sido_codes=sido_codes
            )

            final_count = HospitalCache.objects.count()
            self.total_stats['hospital_stats'] = {
                'existing': existing_count,
                'final': final_count,
                'imported': final_count - existing_count,
                'api_stats': self.hospital_importer.stats.copy()
            }

            logger.info(f"✅ 병원정보 임포트 완료: {final_count - existing_count:,}개 추가")
            return True

        except Exception as e:
            logger.error(f"❌ 병원정보 임포트 실패: {e}")
            self.total_stats['total_errors'] += 1
            return False

    def import_disease_data(self, batch_size=100, delay_seconds=1, search_letters=None):
        """질병 데이터 임포트 (A-Z 검색)"""
        logger.info("🦠 질병정보 임포트 시작 (A-Z 전체 검색)")

        try:
            existing_count = DiseaseCache.objects.count()
            logger.info(f"기존 질병 데이터: {existing_count:,}개")

            # 특정 알파벳만 검색하는 경우
            if search_letters:
                original_letters = self.disease_importer.search_letters
                specified_letters = list(set([letter.upper() for letter in search_letters if letter.isalpha()]))
                self.disease_importer.search_letters = sorted(specified_letters)
                logger.info(f"지정된 알파벳만 검색: {self.disease_importer.search_letters}")

            self.disease_importer.import_all_diseases(
                batch_size=batch_size,
                delay_seconds=delay_seconds
            )

            final_count = DiseaseCache.objects.count()
            self.total_stats['disease_stats'] = {
                'existing': existing_count,
                'final': final_count,
                'imported': final_count - existing_count,
                'api_stats': self.disease_importer.stats.copy()
            }

            logger.info(f"✅ 질병정보 임포트 완료: {final_count - existing_count:,}개 추가")
            return True

        except Exception as e:
            logger.error(f"❌ 질병정보 임포트 실패: {e}")
            self.total_stats['total_errors'] += 1
            return False

    def run_full_import(self, **kwargs):
        """전체 임포트 실행"""
        self.total_stats['start_time'] = datetime.now()

        logger.info("🚀 통합 캐시 데이터 임포트 시작")
        logger.info("=" * 60)

        success_count = 0
        total_tasks = 0

        # 1. 병원 데이터 임포트
        if not kwargs.get('skip_hospital', False):
            total_tasks += 1
            if self.import_hospital_data(
                    batch_size=kwargs.get('batch_size', 100),
                    delay_seconds=kwargs.get('delay', 1),
                    sido_codes=kwargs.get('sido_codes')
            ):
                success_count += 1

            logger.info("-" * 60)
        else:
            logger.info("⏩ 병원 데이터 임포트 건너뛰기")
            logger.info("-" * 60)

        # 2. 질병 데이터 임포트
        if not kwargs.get('skip_disease', False):
            total_tasks += 1
            if self.import_disease_data(
                    batch_size=kwargs.get('batch_size', 100),
                    delay_seconds=kwargs.get('delay', 1),
                    search_letters=kwargs.get('disease_letters')
            ):
                success_count += 1
        else:
            logger.info("⏩ 질병 데이터 임포트 건너뛰기")

        self.total_stats['end_time'] = datetime.now()

        # 최종 결과 출력
        self.print_final_summary()

        return success_count == total_tasks

    def print_final_summary(self):
        """최종 결과 요약 출력"""
        logger.info("=" * 60)
        logger.info("🎉 통합 캐시 데이터 임포트 완료")
        logger.info("=" * 60)

        # 실행 시간 계산
        if self.total_stats['start_time'] and self.total_stats['end_time']:
            duration = self.total_stats['end_time'] - self.total_stats['start_time']
            logger.info(f"⏰ 총 실행 시간: {duration}")

        # 병원 데이터 요약
        if self.total_stats['hospital_stats']:
            hospital_stats = self.total_stats['hospital_stats']
            logger.info(f"\n🏥 병원 데이터:")
            logger.info(f"   기존: {hospital_stats['existing']:,}개")
            logger.info(f"   최종: {hospital_stats['final']:,}개")
            logger.info(f"   추가: {hospital_stats['imported']:,}개")

            api_stats = hospital_stats['api_stats']
            logger.info(f"   API 수신: {api_stats['total_received']:,}개")
            logger.info(f"   생성: {api_stats['created']:,}개")
            logger.info(f"   업데이트: {api_stats['updated']:,}개")
            logger.info(f"   오류: {api_stats['errors']:,}개")

        # 질병 데이터 요약
        if self.total_stats['disease_stats']:
            disease_stats = self.total_stats['disease_stats']
            logger.info(f"\n🦠 질병 데이터:")
            logger.info(f"   기존: {disease_stats['existing']:,}개")
            logger.info(f"   최종: {disease_stats['final']:,}개")
            logger.info(f"   추가: {disease_stats['imported']:,}개")

            api_stats = disease_stats['api_stats']
            logger.info(f"   API 수신: {api_stats['total_received']:,}개")
            logger.info(f"   생성: {api_stats['created']:,}개")
            logger.info(f"   업데이트: {api_stats['updated']:,}개")
            logger.info(f"   오류: {api_stats['errors']:,}개")

        # 전체 통계
        total_imported = 0
        total_api_received = 0
        total_api_errors = 0

        if self.total_stats['hospital_stats']:
            total_imported += self.total_stats['hospital_stats']['imported']
            total_api_received += self.total_stats['hospital_stats']['api_stats']['total_received']
            total_api_errors += self.total_stats['hospital_stats']['api_stats']['errors']

        if self.total_stats['disease_stats']:
            total_imported += self.total_stats['disease_stats']['imported']
            total_api_received += self.total_stats['disease_stats']['api_stats']['total_received']
            total_api_errors += self.total_stats['disease_stats']['api_stats']['errors']

        logger.info(f"\n📊 전체 요약:")
        logger.info(f"   총 추가된 데이터: {total_imported:,}개")
        logger.info(f"   총 API 수신: {total_api_received:,}개")
        logger.info(f"   총 오류: {total_api_errors + self.total_stats['total_errors']:,}개")

        # 성공률 계산
        if total_api_received > 0:
            success_rate = ((total_api_received - total_api_errors) / total_api_received) * 100
            logger.info(f"   전체 성공률: {success_rate:.2f}%")

        logger.info("=" * 60)

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='통합 캐시 데이터 임포트 스크립트')

    # 필수 인자
    parser.add_argument('--api-key', type=str, required=True, help='공공데이터포털 API 키')

    # 공통 옵션
    parser.add_argument('--batch-size', type=int, default=100, help='배치 크기 (최대 1000)')
    parser.add_argument('--delay', type=float, default=1.0, help='API 호출 간 딜레이(초)')

    # 병원 데이터 옵션
    parser.add_argument('--skip-hospital', action='store_true', help='병원 데이터 임포트 건너뛰기')
    parser.add_argument('--sido-codes', type=str, nargs='+', help='특정 시도코드만 수집 (예: 11 26 27)')
    parser.add_argument('--hospital-types', type=str, nargs='+',
                        default=['01', '11', '21'],
                        help='수집할 종별코드 (기본값: 01 11 21 - 상급종합병원, 종합병원, 병원)')

    # 질병 데이터 옵션
    parser.add_argument('--skip-disease', action='store_true', help='질병 데이터 임포트 건너뛰기')
    parser.add_argument('--disease-letters', type=str, nargs='+', help='질병 검색할 알파벳 (예: A B C)')

    # 개별 실행 옵션
    parser.add_argument('--hospital-only', action='store_true', help='병원 데이터만 임포트')
    parser.add_argument('--disease-only', action='store_true', help='질병 데이터만 임포트')

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
    importer = UnifiedCacheImporter(args.api_key)

    try:
        if args.hospital_only:
            # 병원 데이터만 임포트
            logger.info("병원 데이터만 임포트합니다.")
            success = importer.import_hospital_data(
                batch_size=args.batch_size,
                delay_seconds=args.delay,
                sido_codes=args.sido_codes
            )

        elif args.disease_only:
            # 질병 데이터만 임포트
            logger.info("질병 데이터만 임포트합니다.")
            success = importer.import_disease_data(
                batch_size=args.batch_size,
                delay_seconds=args.delay,
                search_letters=args.disease_letters
            )

        else:
            # 통합 임포트 실행
            success = importer.run_full_import(
                batch_size=args.batch_size,
                delay=args.delay,
                sido_codes=args.sido_codes if not args.skip_hospital else None,
                search_letters=args.disease_letters if not args.skip_disease else None,
                disease_full_import=args.disease_full_import if not args.skip_disease else False,
                skip_hospital=args.skip_hospital,
                skip_disease=args.skip_disease
            )

        if success:
            logger.info("✅ 모든 임포트가 성공적으로 완료되었습니다!")
            sys.exit(0)
        else:
            logger.error("❌ 일부 임포트가 실패했습니다.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
        importer.print_final_summary()
        sys.exit(1)
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# 사용 예시:
"""
# 기본 실행 (상급종합병원, 종합병원, 병원 + A-Z 전체 질병검색)
python import_all_cache_data.py --api-key YOUR_API_KEY

# 상급종합병원만 + A, B, C 알파벳 질병만
python import_all_cache_data.py --api-key YOUR_API_KEY --hospital-types 01 --disease-letters A B C

# 병원 데이터만 임포트 (서울지역 상급종합병원과 종합병원)
python import_all_cache_data.py --api-key YOUR_API_KEY --hospital-only --sido-codes 11 --hospital-types 01 11

# 질병 데이터만 임포트 (특정 알파벳)
python import_all_cache_data.py --api-key YOUR_API_KEY --disease-only --disease-letters A M Z

# 질병 데이터만 전체 A-Z 검색
python import_all_cache_data.py --api-key YOUR_API_KEY --disease-only

# 병원은 건너뛰고 질병만 A-F 알파벳 검색
python import_all_cache_data.py --api-key YOUR_API_KEY --skip-hospital --disease-letters A B C D E F

# 상급종합병원만 + 질병 A-E 알파벳만
python import_all_cache_data.py --api-key YOUR_API_KEY --hospital-types 01 --disease-letters A B C D E

# 배치 크기와 딜레이 조정
python import_all_cache_data.py --api-key YOUR_API_KEY --hospital-types 01 11 21 --batch-size 50 --delay 2
"""