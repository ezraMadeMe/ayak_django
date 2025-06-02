#!/usr/bin/env python
"""
건강보험심사평가원 약가마스터 데이터를 사용하여 MainIngredient 테이블을 채우는 스크립트

사용법:
1. Django 프로젝트 루트에서 실행
2. python manage.py shell < populate_main_ingredient2.py
또는
3. python populate_main_ingredient2.py (Django 설정이 된 상태에서)
"""

import os
import sys
import django
import csv
import logging
from decimal import Decimal, InvalidOperation
from collections import defaultdict
import django; django.setup()

# Django 설정
if __name__ == "__main__":
    # Django 설정 파일 경로 설정 (프로젝트에 맞게 수정)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yakun.settings')
    django.setup()

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError
from user.models import MainIngredient  # 실제 앱 이름으로 변경

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_ingredient_import.logs', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MainIngredientImporter:
    """주성분 데이터 임포터 클래스"""

    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path
        self.stats = {
            'total_rows': 0,
            'processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        self.error_details = []

    def clean_data(self, row):
        """데이터 정리 및 검증"""
        try:
            # 필수 필드 검증
            ingr_code = str(row.get('일반명코드', '')).strip()
            if not ingr_code:
                raise ValueError("일반명코드가 없습니다")

            # 일반명 처리 (한글명과 영문명 분리)
            ingredient_name = str(row.get('일반명', '')).strip()
            if not ingredient_name:
                raise ValueError("일반명이 없습니다")

            # 영문명과 한글명 분리 (영문이 포함된 경우)
            if any(ord(char) < 128 for char in ingredient_name):
                # 영문이 포함된 경우 영문명으로 처리
                main_ingr_name_en = ingredient_name
                main_ingr_name_kr = ''
            else:
                # 순수 한글인 경우
                main_ingr_name_kr = ingredient_name
                main_ingr_name_en = ''

            # 함량 처리
            density_str = str(row.get('함량', '0')).strip()
            try:
                # 함량에서 숫자만 추출 (예: "1.1g(55mg/mL)" -> "1.1")
                import re
                numeric_part = re.search(r'[\d.]+', density_str)
                if numeric_part:
                    density = Decimal(numeric_part.group())
                else:
                    density = Decimal('0')
            except (InvalidOperation, ValueError):
                density = Decimal('0')

            # 단위 처리
            unit = str(row.get('단위', '')).strip()
            if not unit:
                unit = 'mg'  # 기본 단위

            # 단위에서 괄호 부분 제거 (예: "g(55mg/mL)" -> "g")
            import re
            unit = re.sub(r'\([^)]*\)', '', unit).strip()

            return {
                'ingr_code': ingr_code,
                'main_ingr_name_kr': main_ingr_name_kr,
                'main_ingr_name_en': main_ingr_name_en,
                'main_ingr_density': density,
                'main_ingr_unit': unit,
                'dosage_form': str(row.get('제형', '')).strip(),
                'route': str(row.get('투여경로', '')).strip(),
                'classification': row.get('분류번호', 0)
            }

        except Exception as e:
            raise ValueError(f"데이터 정리 중 오류: {str(e)}")

    def process_duplicates(self, cleaned_data_list):
        """중복 데이터 처리 - 동일한 성분코드에 대해 최적의 데이터 선택"""
        grouped_data = defaultdict(list)

        # 성분코드별로 그룹화
        for data in cleaned_data_list:
            grouped_data[data['ingr_code']].append(data)

        processed_data = []

        for ingr_code, data_list in grouped_data.items():
            if len(data_list) == 1:
                processed_data.append(data_list[0])
            else:
                # 중복된 경우 최적의 데이터 선택
                # 1. 한글명이 있는 것 우선
                # 2. 함량이 0이 아닌 것 우선
                # 3. 단위가 명확한 것 우선
                best_data = max(data_list, key=lambda x: (
                    bool(x['main_ingr_name_kr']),
                    x['main_ingr_density'] > 0,
                    bool(x['main_ingr_unit']) and x['main_ingr_unit'] != 'mg'
                ))

                # 영문명이 없다면 다른 데이터에서 가져오기
                if not best_data['main_ingr_name_en']:
                    for data in data_list:
                        if data['main_ingr_name_en']:
                            best_data['main_ingr_name_en'] = data['main_ingr_name_en']
                            break

                processed_data.append(best_data)
                logger.info(f"중복 데이터 병합: {ingr_code} ({len(data_list)}개 -> 1개)")

        return processed_data

    def create_or_update_ingredient(self, data):
        """주성분 생성 또는 업데이트"""
        try:
            ingredient, created = MainIngredient.objects.update_or_create(
                ingr_code=data['ingr_code'],
                defaults={
                    'main_ingr_name_kr': data['main_ingr_name_kr'],
                    'main_ingr_name_en': data['main_ingr_name_en'],
                    'main_ingr_density': data['main_ingr_density'],
                    'main_ingr_unit': data['main_ingr_unit'],
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
            error_msg = f"DB 저장 오류 - 코드: {data['ingr_code']}, 오류: {str(e)}"
            self.error_details.append(error_msg)
            logger.error(error_msg)
            return 'error'

    def import_data(self, batch_size=1000, dry_run=False):
        """CSV 데이터 임포트"""
        logger.info(f"데이터 임포트 시작: {self.csv_file_path}")
        logger.info(f"배치 크기: {batch_size}, 드라이런: {dry_run}")

        try:
            with open(self.csv_file_path, 'r', encoding='euc-kr') as csvfile:
                # CSV 리더 생성
                reader = csv.DictReader(csvfile)

                cleaned_data_list = []
                batch_count = 0

                for row_num, row in enumerate(reader, 1):
                    self.stats['total_rows'] += 1

                    try:
                        # 데이터 정리
                        cleaned_data = self.clean_data(row)
                        cleaned_data_list.append(cleaned_data)
                        self.stats['processed'] += 1

                        # 배치 처리
                        if len(cleaned_data_list) >= batch_size:
                            batch_count += 1
                            self._process_batch(cleaned_data_list, batch_count, dry_run)
                            cleaned_data_list = []

                    except ValueError as e:
                        self.stats['skipped'] += 1
                        error_msg = f"행 {row_num} 스킵: {str(e)}"
                        self.error_details.append(error_msg)
                        logger.warning(error_msg)
                        continue

                # 마지막 배치 처리
                if cleaned_data_list:
                    batch_count += 1
                    self._process_batch(cleaned_data_list, batch_count, dry_run)

        except FileNotFoundError:
            logger.error(f"파일을 찾을 수 없습니다: {self.csv_file_path}")
            return False
        except UnicodeDecodeError:
            logger.error("파일 인코딩 오류. EUC-KR 인코딩을 확인하세요.")
            return False
        except Exception as e:
            logger.error(f"예상치 못한 오류: {str(e)}")
            return False

        return True

    def _process_batch(self, cleaned_data_list, batch_num, dry_run):
        """배치 처리"""
        logger.info(f"배치 {batch_num} 처리 중... ({len(cleaned_data_list)}개 데이터)")

        # 중복 데이터 처리
        processed_data = self.process_duplicates(cleaned_data_list)

        if dry_run:
            logger.info(f"드라이런: 배치 {batch_num}에서 {len(processed_data)}개 데이터 처리 예정")
            return

        # 트랜잭션으로 배치 처리
        try:
            with transaction.atomic():
                for data in processed_data:
                    result = self.create_or_update_ingredient(data)

                    if result in ['created', 'updated']:
                        logger.debug(
                            f"{result}: {data['ingr_code']} - {data['main_ingr_name_kr'] or data['main_ingr_name_en']}")

        except Exception as e:
            logger.error(f"배치 {batch_num} 처리 중 오류: {str(e)}")
            self.stats['errors'] += len(processed_data)

    def print_summary(self):
        """처리 결과 요약 출력"""
        logger.info("=" * 50)
        logger.info("데이터 임포트 완료")
        logger.info("=" * 50)
        logger.info(f"총 행 수: {self.stats['total_rows']:,}")
        logger.info(f"처리된 행: {self.stats['processed']:,}")
        logger.info(f"생성된 데이터: {self.stats['created']:,}")
        logger.info(f"업데이트된 데이터: {self.stats['updated']:,}")
        logger.info(f"스킵된 행: {self.stats['skipped']:,}")
        logger.info(f"오류 발생: {self.stats['errors']:,}")

        if self.error_details:
            logger.info("\n주요 오류 내용 (최대 10개):")
            for error in self.error_details[:10]:
                logger.info(f"  - {error}")

        # 성공률 계산
        success_rate = (self.stats['created'] + self.stats['updated']) / max(self.stats['processed'], 1) * 100
        logger.info(f"\n성공률: {success_rate:.2f}%")


def main():
    """메인 실행 함수"""
    # CSV 파일 경로 (실제 경로로 수정 필요)
    csv_file_path = '건강보험심사평가원_약가마스터_의약품주성분_20241014.csv'

    # 임포터 생성
    importer = MainIngredientImporter(csv_file_path)

    # 옵션 설정
    BATCH_SIZE = 1000  # 배치 크기
    DRY_RUN = False  # True로 설정하면 실제 DB에 저장하지 않고 시뮬레이션만

    # 시작 전 확인
    if DRY_RUN:
        logger.info("드라이런 모드: 실제 데이터베이스에 저장하지 않습니다.")

    # 기존 데이터 수 확인
    existing_count = MainIngredient.objects.count()
    logger.info(f"기존 MainIngredient 데이터 수: {existing_count:,}")

    # 데이터 임포트 실행
    success = importer.import_data(batch_size=BATCH_SIZE, dry_run=DRY_RUN)

    if success:
        # 결과 요약 출력
        importer.print_summary()

        # 최종 데이터 수 확인
        if not DRY_RUN:
            final_count = MainIngredient.objects.count()
            logger.info(f"최종 MainIngredient 데이터 수: {final_count:,}")
            logger.info(f"증가한 데이터 수: {final_count - existing_count:,}")
    else:
        logger.error("데이터 임포트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()


# Django shell에서 직접 사용하는 경우
def run_import(csv_path=None, dry_run=True):
    """Django shell에서 직접 실행하는 함수"""
    if csv_path is None:
        csv_path = '건강보험심사평가원_약가마스터_의약품주성분_20241014.csv'

    importer = MainIngredientImporter(csv_path)
    success = importer.import_data(batch_size=500, dry_run=dry_run)

    if success:
        importer.print_summary()
        return importer.stats
    else:
        return None


# 사용 예시:
"""
# Django shell에서 실행:
python manage.py shell

>>> from populate_main_ingredient import run_import
>>> # 먼저 드라이런으로 테스트
>>> stats = run_import(dry_run=True)
>>> # 문제없으면 실제 실행
>>> stats = run_import(dry_run=False)

# 또는 스크립트 직접 실행:
python populate_main_ingredient2.py
"""