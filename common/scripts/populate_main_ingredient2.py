#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
건강보험심사평가원 약가마스터 데이터를 사용하여 MainIngredient 테이블을 채우는 스크립트

사용법:
1. Django 프로젝트 루트에서 실행
2. python manage.py shell < populate_main_ingredient.py
또는
3. python populate_main_ingredient.py (Django 설정이 된 상태에서)
"""

import os
import sys
import django
import csv
import logging
import chardet
import pandas as pd
from io import StringIO

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# DJANGO_SETTINGS_MODULE 환경 변수를 설정합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')

# Django를 설정합니다.
django.setup()

from decimal import Decimal, InvalidOperation
from collections import defaultdict
from user.models import MainIngredient
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main_ingredient_import.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def detect_and_convert_csv(file_path):
    """CSV 파일의 인코딩을 감지하고 올바른 형태로 변환"""
    # 한국어 CSV 파일에 대해 확실한 인코딩 시도
    encodings_to_try = [
        ('euc-kr', 'EUC-KR'),
        ('cp949', 'CP949'),
        ('utf-8', 'UTF-8'),
        ('utf-8-sig', 'UTF-8 with BOM'),
        ('cp1252', 'CP1252'),
        ('latin-1', 'Latin-1')
    ]

    for encoding, encoding_name in encodings_to_try:
        try:
            logger.info(f"인코딩 시도: {encoding_name}")

            # pandas로 파일 읽기 시도
            df = pd.read_csv(file_path, encoding=encoding, low_memory=False)

            # 컬럼명 확인
            columns = df.columns.tolist()
            logger.info(f"읽어온 컬럼명: {columns}")

            # 한글이 제대로 읽혔는지 확인
            sample_columns = str(columns)

            # 한글 컬럼명이 올바르게 읽혔는지 체크
            if '일반명코드' in columns and '일반명' in columns:
                logger.info("✓ 한글 컬럼명이 올바르게 인식되었습니다.")
                valid_encoding = True
            elif len(columns) == 8:  # 예상 컬럼 수와 일치
                # 컬럼명이 깨졌지만 개수가 맞다면 강제 매핑
                expected_columns = ['일반명코드', '제형구분코드', '제형', '일반명', '분류번호', '투여', '함량', '단위']
                column_mapping = {old_col: new_col for old_col, new_col in zip(columns, expected_columns)}
                df = df.rename(columns=column_mapping)
                logger.info(f"✓ 컬럼명을 강제 매핑했습니다: {encoding_name}")
                logger.info(f"매핑: {column_mapping}")
                valid_encoding = True
            else:
                logger.warning(f"✗ 예상과 다른 컬럼 구조: {columns}")
                valid_encoding = False
                continue

            if valid_encoding:
                # 데이터 샘플 확인
                logger.info(f"총 {len(df)} 행 읽음")
                if len(df) > 0:
                    sample_row = df.iloc[0].to_dict()
                    logger.info(f"첫 번째 행 샘플:")
                    for key, value in sample_row.items():
                        logger.info(f"  {key}: {value}")

                    # 실제 데이터에 한글이 제대로 있는지 확인
                    ingredient_name = sample_row.get('일반명', '')
                    if ingredient_name and len(str(ingredient_name).strip()) > 0:
                        logger.info(f"✓ 성공: {encoding_name} 인코딩으로 파일을 읽었습니다.")
                        return df, encoding
                    else:
                        logger.warning(f"✗ 일반명 데이터가 비어있습니다: {ingredient_name}")
                        continue
                else:
                    logger.warning("✗ 데이터가 비어있습니다.")
                    continue

        except UnicodeDecodeError as e:
            logger.warning(f"✗ {encoding_name} 인코딩 실패: {e}")
            continue
        except Exception as e:
            logger.warning(f"✗ {encoding_name} 인코딩으로 읽기 실패: {e}")
            continue

    raise Exception("지원하는 인코딩을 찾을 수 없습니다. CSV 파일의 인코딩을 확인해주세요.")


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
            # pandas Series에서 안전하게 값 가져오기
            def safe_get(series, key, default=''):
                try:
                    value = series.get(key, default)
                    if pd.isna(value) or value is None:
                        return default
                    return str(value).strip()
                except:
                    return default

            def safe_get_numeric(series, key, default=0):
                try:
                    value = series.get(key, default)
                    if pd.isna(value) or value is None:
                        return default
                    return value
                except:
                    return default

            # 필수 필드 검증
            ingr_code = safe_get(row, '일반명코드')
            if not ingr_code or ingr_code == 'nan' or len(ingr_code.strip()) == 0:
                raise ValueError("일반명코드가 없습니다")

            # 일반명 처리
            ingredient_name = safe_get(row, '일반명')
            if not ingredient_name or ingredient_name == 'nan' or len(ingredient_name.strip()) == 0:
                raise ValueError("일반명이 없습니다")

            # 영문명과 한글명 분리 (영문 문자가 포함되어 있는지 확인)
            has_english = any(c.isascii() and c.isalpha() for c in ingredient_name)
            has_korean = any('\uac00' <= c <= '\ud7af' for c in ingredient_name)

            if has_english and not has_korean:
                # 순수 영문
                main_ingr_name_en = ingredient_name
                main_ingr_name_kr = ''
            elif has_korean and not has_english:
                # 순수 한글
                pass
                # main_ingr_name_kr = ingredient_name
                # main_ingr_name_en = ''
            elif has_english and has_korean:
                # 혼합된 경우 - 둘 다 저장
                main_ingr_name_kr = ingredient_name
                main_ingr_name_en = ingredient_name
            else:
                # 기타 문자 (숫자, 특수문자 등)
                pass
                # main_ingr_name_kr = ingredient_name
                # main_ingr_name_en = ''

            # 함량 처리
            density_value = safe_get_numeric(row, '함량', 0)
            try:
                if isinstance(density_value, (int, float)):
                    density = Decimal(str(density_value))
                else:
                    # 문자열인 경우 숫자 부분만 추출
                    import re
                    density_str = str(density_value)
                    numeric_match = re.search(r'[\d.]+', density_str)
                    if numeric_match:
                        density = Decimal(numeric_match.group())
                    else:
                        density = Decimal('0')
            except (InvalidOperation, ValueError, TypeError):
                density = Decimal('0')

            # 단위 처리
            unit = safe_get(row, '단위', 'mg')
            if not unit or unit == 'nan' or len(unit.strip()) == 0:
                unit = 'mg'

            # 단위에서 괄호 부분 제거
            import re
            unit = re.sub(r'\([^)]*\)', '', unit).strip()
            if not unit:
                unit = 'mg'

            # 분류번호 처리
            classification = safe_get_numeric(row, '분류번호', 0)
            try:
                classification = int(classification) if classification else 0
            except (ValueError, TypeError):
                classification = 0

            # 제형구분코드 및 제형
            dosage_form_code = safe_get(row, '제형구분코드')
            dosage_form = safe_get(row, '제형')

            # 원본함량표기 (함량과 단위를 조합)
            original_density_str = f"{density_value}{unit}" if density_value else safe_get(row, '함량')

            # 복합제 판정
            is_combination = self.determine_combination_drug(ingredient_name, dosage_form, original_density_str)

            return {
                'ingr_code': ingr_code,  # 원본일반명코드
                'main_ingr_name_kr': main_ingr_name_kr,
                'main_ingr_name_en': main_ingr_name_en,
                'main_ingr_density': density,
                'main_ingr_unit': unit,
                'dosage_form_code': dosage_form_code,  # 제형구분코드
                'dosage_form': dosage_form,  # 제형
                'route': safe_get(row, '투여'),
                'classification': classification,  # 분류번호
                'original_density_notation': original_density_str,  # 원본함량표기
                'is_combination_drug': is_combination  # 복합제 여부
            }

        except Exception as e:
            raise ValueError(f"데이터 정리 중 오류: {str(e)}")

    def determine_combination_drug(self, ingredient_name, dosage_form, density_str):
        """복합제 여부 판정"""
        # 1. 일반명에 복합제 표시자가 있는지 확인
        combination_indicators = ['+', '및', '과', '배합', '복합', '혼합']

        for indicator in combination_indicators:
            if indicator in ingredient_name:
                return True

        # 2. 제형에 복합 표시가 있는지 확인
        if dosage_form and ('복합' in dosage_form or '배합' in dosage_form):
            return True

        # 3. 함량 표기에 여러 성분이 표시된 경우 (괄호 안에 다른 함량이 있는 경우)
        import re
        if re.search(r'\([^)]*\d+[^)]*\)', str(density_str)):
            return True

        # 4. 일반명에 여러 성분명이 나열된 경우 (영문명이 2개 이상인 경우)
        # 영문 단어가 2개 이상이고 and, with 등이 포함된 경우
        english_words = re.findall(r'[a-zA-Z]+', ingredient_name)
        if len(english_words) >= 2 and any(word.lower() in ['and', 'with', 'plus'] for word in english_words):
            return True

        return False

    def process_duplicates(self, cleaned_data_list):
        """중복 데이터 처리 - 더 정교한 로직으로 개선"""
        grouped_data = defaultdict(list)

        for data in cleaned_data_list:
            grouped_data[data['ingr_code']].append(data)

        processed_data = []

        for ingr_code, data_list in grouped_data.items():
            if len(data_list) == 1:
                processed_data.append(data_list[0])
            else:
                # 중복된 경우 더 정교한 선택 로직
                # 우선순위:
                # 1. 복합제가 아닌 것 우선 (단일 성분 우선)
                # 2. 한글명이 있는 것 우선
                # 3. 함량이 0이 아닌 것 우선
                # 4. 제형 정보가 상세한 것 우선
                best_data = max(data_list, key=lambda x: (
                    not x['is_combination_drug'],  # 단일성분 우선
                    bool(x['main_ingr_name_kr']),  # 한글명 있는 것 우선
                    x['main_ingr_density'] > 0,  # 함량 정보가 있는 것
                    len(x['dosage_form']),  # 제형 정보가 상세한 것
                    bool(x['dosage_form_code'])  # 제형코드가 있는 것
                ))

                # 영문명이 없다면 다른 데이터에서 보완
                if not best_data['main_ingr_name_en']:
                    for data in data_list:
                        if data['main_ingr_name_en']:
                            best_data['main_ingr_name_en'] = data['main_ingr_name_en']
                            break

                # 제형 정보 보완
                if not best_data['dosage_form']:
                    for data in data_list:
                        if data['dosage_form']:
                            best_data['dosage_form'] = data['dosage_form']
                            break

                processed_data.append(best_data)

                # 중복 제거 상세 로그
                logger.debug(f"중복 데이터 병합: {ingr_code} ({len(data_list)}개 -> 1개)")
                logger.debug(f"  선택된 데이터: {best_data['main_ingr_name_kr'] or best_data['main_ingr_name_en']}")
                logger.debug(f"  복합제 여부: {best_data['is_combination_drug']}")

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
                    'dosage_form_code': data['dosage_form_code'],
                    'dosage_form': data['dosage_form'],
                    'route': data['route'],
                    'classification': data['classification'],
                    'original_density_notation': data['original_density_notation'],
                    'is_combination_drug': data['is_combination_drug'],
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

    def import_data(self, batch_size=500, dry_run=False):
        """CSV 데이터 임포트 - pandas 사용하여 대용량 파일 처리"""
        logger.info(f"데이터 임포트 시작: {self.csv_file_path}")
        logger.info(f"배치 크기: {batch_size}, 드라이런: {dry_run}")

        try:
            # CSV 파일 읽기
            df, encoding = detect_and_convert_csv(self.csv_file_path)
            logger.info(f"사용된 인코딩: {encoding}")

            self.stats['total_rows'] = len(df)
            logger.info(f"총 {self.stats['total_rows']} 행을 처리합니다.")

            cleaned_data_list = []
            batch_count = 0

            # 청크 단위로 처리하여 메모리 효율성 증대
            chunk_size = batch_size
            for start_idx in range(0, len(df), chunk_size):
                end_idx = min(start_idx + chunk_size, len(df))
                chunk = df.iloc[start_idx:end_idx]

                logger.info(f"처리 중: {start_idx + 1}~{end_idx} 행 ({len(chunk)} 행)")

                for idx, row in chunk.iterrows():
                    try:
                        cleaned_data = self.clean_data(row)
                        cleaned_data_list.append(cleaned_data)
                        self.stats['processed'] += 1

                    except ValueError as e:
                        self.stats['skipped'] += 1
                        error_msg = f"행 {idx + 1} 스킵: {str(e)}"
                        self.error_details.append(error_msg)
                        if len(self.error_details) <= 20:  # 처음 20개 오류만 로깅
                            logger.warning(error_msg)
                        continue

                # 배치 처리
                if cleaned_data_list:
                    batch_count += 1
                    self._process_batch(cleaned_data_list, batch_count, dry_run)
                    cleaned_data_list = []

                # 진행상황 로깅
                if batch_count % 10 == 0:
                    progress = (end_idx / len(df)) * 100
                    logger.info(f"진행률: {progress:.1f}% ({end_idx}/{len(df)} 행)")

        except Exception as e:
            logger.error(f"파일 처리 중 오류: {str(e)}")
            return False

        return True

    def _process_batch(self, cleaned_data_list, batch_num, dry_run):
        """배치 처리"""
        logger.debug(f"배치 {batch_num} 처리 중... ({len(cleaned_data_list)}개 데이터)")

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
            logger.info(f"\n주요 오류 내용 (총 {len(self.error_details)}개 중 최대 10개):")
            for error in self.error_details[:10]:
                logger.info(f"  - {error}")

        # 성공률 계산
        if self.stats['processed'] > 0:
            success_rate = (self.stats['created'] + self.stats['updated']) / self.stats['processed'] * 100
            logger.info(f"\n성공률: {success_rate:.2f}%")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='주성분 데이터 임포트 스크립트')
    parser.add_argument('--csv', type=str, help='CSV 파일 경로', default='../data/main_ingr.csv')
    parser.add_argument('--batch-size', type=int, help='배치 크기', default=500)
    parser.add_argument('--dry-run', action='store_true', help='실제 DB 저장 없이 시뮬레이션만 실행')

    args = parser.parse_args()

    # 임포터 생성
    importer = MainIngredientImporter(args.csv)

    # 시작 전 확인
    if args.dry_run:
        logger.info("드라이런 모드: 실제 데이터베이스에 저장하지 않습니다.")

    # 기존 데이터 수 확인
    existing_count = MainIngredient.objects.count()
    logger.info(f"기존 MainIngredient 데이터 수: {existing_count:,}")

    # 데이터 임포트 실행
    success = importer.import_data(batch_size=args.batch_size, dry_run=args.dry_run)

    if success:
        # 결과 요약 출력
        importer.print_summary()

        # 최종 데이터 수 확인
        if not args.dry_run:
            final_count = MainIngredient.objects.count()
            logger.info(f"최종 MainIngredient 데이터 수: {final_count:,}")
            logger.info(f"증가한 데이터 수: {final_count - existing_count:,}")
    else:
        logger.error("데이터 임포트 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()


# Django shell에서 직접 사용하는 경우
def run_import(csv_path=None, dry_run=True, batch_size=500):
    """Django shell에서 직접 실행하는 함수"""
    if csv_path is None:
        csv_path = '../data/main_ingr.csv'

    importer = MainIngredientImporter(csv_path)
    success = importer.import_data(batch_size=batch_size, dry_run=dry_run)

    if success:
        importer.print_summary()
        return importer.stats
    else:
        return None