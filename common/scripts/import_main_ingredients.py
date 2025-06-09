#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MainIngredient 테이블 임포터 스크립트

의약품표준코드.xlsx와 의약품주성분csv.xlsx 파일을 분석하여
MainIngredient 테이블을 구성합니다.

사용법:
python import_main_ingredients.py --standard-code-file "의약품표준코드2.xlsx" --ingredient-file "의약품주성분csv.xlsx"
"""

import os
import sys
import django
import pandas as pd
import numpy as np
import requests
import xml.etree.ElementTree as ET
import re
import hashlib
import logging
import time
from decimal import Decimal
from datetime import datetime

# Django 설정
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')
django.setup()

from user.models import MainIngredient
from django.db import transaction, IntegrityError, models
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


class MainIngredientImporter:
    """MainIngredient 임포터 클래스"""

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.drug_api_url = "http://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService06/getDrugPrdtPrmsnDtlInq05"

        self.stats = {
            'total_standard_codes': 0,
            'valid_codes': 0,
            'combination_drugs': 0,
            'single_ingredients': 0,
            'api_calls': 0,
            'api_success': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        self.error_details = []

        # 단위 매핑 테이블
        self.unit_mapping = {
            '밀리그램': 'mg',
            'mg': 'mg',
            '그램': 'g',
            'g': 'g',
            '㎍': 'mcg',
            'mcg': 'mcg',
            '밀리리터': 'ml',
            'ml': 'ml',
            'mL': 'ml',
            '리터': 'L',
            'L': 'L',
            '퍼센트': '%',
            '%': '%',
            'IU': 'IU',
            'μg': 'mcg',
            'ng': 'ng',
            'pg': 'pg'
        }

    def load_standard_code_data(self, file_path):
        """의약품표준코드 데이터 로드 (전문의약품만, 주사제형 제외)"""
        logger.info(f"의약품표준코드 파일 로드: {file_path}")

        try:
            # 엑셀 파일 읽기
            df = pd.read_excel(file_path, engine='openpyxl')

            # 필요한 컬럼만 선택
            required_columns = ['일반명코드(성분명코드)', 'ATC코드', '약품규격', '한글상품명', '전문_일반', '제형구분', '표준코드']
            df = df[required_columns].copy()

            # 컬럼명 단순화
            df.columns = ['일반명코드', 'ATC코드', '약품규격', '상품명', '전문일반', '제형구분', '표준코드']

            logger.info(f"원본 데이터: {len(df):,}개")

            # 일반명코드가 있는 데이터만 필터링
            df = df[df['일반명코드'].notna()].copy()
            df['일반명코드'] = df['일반명코드'].astype(str).str.strip()
            df = df[df['일반명코드'] != ''].copy()

            logger.info(f"일반명코드 있는 데이터: {len(df):,}개")

            # 전문의약품만 필터링
            df = df[df['전문일반'].str.contains('전문', na=False)].copy()
            logger.info(f"전문의약품 필터링 후: {len(df):,}개")

            # 주사제형 제외
            injection_keywords = ['주사', '인젝션', 'injection', '바이알', 'vial', '앰플', 'ampoule', '프리필드']
            injection_mask = df['제형구분'].astype(str).str.contains('|'.join(injection_keywords), case=False, na=False)
            df = df[~injection_mask].copy()
            logger.info(f"주사제형 제외 후: {len(df):,}개")

            # 중복 제거 (일반명코드 기준)
            df = df.drop_duplicates(subset=['일반명코드'], keep='first')
            logger.info(f"중복 제거 후 최종 데이터: {len(df):,}개")

            return df

        except Exception as e:
            logger.error(f"의약품표준코드 파일 로드 실패: {e}")
            return None

    def load_ingredient_data(self, file_path):
        """의약품주성분 데이터 로드"""
        logger.info(f"의약품주성분 파일 로드: {file_path}")

        try:
            # 엑셀 파일 읽기
            df = pd.read_excel(file_path, engine='openpyxl')

            # 필요한 컬럼만 선택
            required_columns = ['일반명코드', '일반명', '함량', '단위']
            df = df[required_columns].copy()

            # 일반명코드가 있는 데이터만 필터링
            df = df[df['일반명코드'].notna()].copy()
            df['일반명코드'] = df['일반명코드'].astype(str).str.strip()

            logger.info(f"로드된 성분 데이터: {len(df)}개")
            return df

        except Exception as e:
            logger.error(f"의약품주성분 파일 로드 실패: {e}")
            return None

    def parse_dosage_info(self, dosage_text):
        """약품규격에서 함량과 단위 추출"""
        if pd.isna(dosage_text) or str(dosage_text).strip() in ['', '없음']:
            return 0, ''

        dosage_str = str(dosage_text).strip()

        # 숫자와 단위 분리 정규식
        pattern = r'(\d+(?:\.\d+)?)\s*([가-힣A-Za-z%]+)'
        match = re.search(pattern, dosage_str)

        if match:
            amount = float(match.group(1))
            unit = match.group(2)

            # 단위 표준화
            standardized_unit = self.unit_mapping.get(unit, unit)
            return amount, standardized_unit

        # 숫자만 있는 경우
        number_match = re.search(r'(\d+(?:\.\d+)?)', dosage_str)
        if number_match:
            return float(number_match.group(1)), 'mg'  # 기본 단위

        return 0, ''

    def extract_korean_english_names(self, name_text, product_name=None, bar_code=None):
        """일반명에서 한글명과 영문명 분리 (API로 국문명 보완)"""
      #  global korean_name, english_name

        if pd.isna(name_text) or not name_text:
            korean_name = ''
            english_name = ''
        else:
            name_str = str(name_text).strip()

            # 괄호 제거
            name_clean = re.sub(r'\([^)]*\)', '', name_str).strip()

            # 한글과 영문 분리
            korean_pattern = r'[가-힣\s]+'
            english_pattern = r'[A-Za-z\s\-]+'

            korean_match = re.search(korean_pattern, name_clean)
            english_match = re.search(english_pattern, name_clean)

            korean_name = korean_match.group().strip() if korean_match else ''
            english_name = english_match.group().strip() if english_match else ''

            # (as xxx) 형태 제거
            english_name = re.sub(r'\s*\(as\s+[^)]+\)', '', english_name).strip()

        # 영문명만 있거나 둘 다 없는 경우 API로 한글명 검색
        if (english_name and not korean_name) or (not english_name and not korean_name):
            if bar_code and self.api_key:
                logger.debug(f"API로 성분명 검색: 영문명={english_name}, 표준코드={bar_code}")
                api_result = self.call_drug_api(bar_code)
                if api_result and api_result[0]:  # 한글명이 있으면
                    korean_name = api_result[0]
                    if api_result[1] and not english_name:  # 영문명도 없었다면 API에서 가져온 것 사용
                        english_name = api_result[1]
                    logger.info(f"API에서 성분명 찾음: {korean_name} / {english_name}")
                    time.sleep(0.5)  # API 호출 제한

        return korean_name, english_name

    def is_combination_drug_code(self, ingredient_df, code):
        """해당 일반명코드가 복합제인지 판단"""
        code_entries = ingredient_df[ingredient_df['일반명코드'] == code]
        return len(code_entries) > 1

    def generate_combination_group(self, code):
        """복합제 그룹 ID 생성"""
        # 일반명코드를 기반으로 해시 생성 (12자리로 제한)
        hash_obj = hashlib.md5(code.encode('utf-8'))
        return hash_obj.hexdigest()[:12]

    def call_drug_api(self, product_name):
        """의약품 API 호출"""
        if not self.api_key:
            return None

        params = {
            'serviceKey': self.api_key,
            'pageNo': '1',
            'numOfRows': '10',
            # 'item_name': product_name,
            'bar_code' : product_name,
            'type': 'xml'
        }

        try:
            self.stats['api_calls'] += 1
            response = requests.get(self.drug_api_url, params=params, timeout=10)
            response.raise_for_status()
            logger.info(f"API : {response.url}")

            # XML 파싱
            root = ET.fromstring(response.text)

            # 결과 확인
            result_code = root.find('.//resultCode')
            if result_code is not None and result_code.text == '00':
                items = root.findall('.//item')
                if items:
                    self.stats['api_success'] += 1
                    item = items[0]

                    # 주성분 정보 추출
                    main_ingr = item.find('MAIN_ITEM_INGR')
                    main_ingr_eng = item.find('MAIN_INGR_ENG')

                    korean_name = main_ingr.text.strip() if main_ingr is not None and main_ingr.text else ''
                    english_name = main_ingr_eng.text.strip() if main_ingr_eng is not None and main_ingr_eng.text else ''

                    # 괄호 제거
                    korean_name = re.sub(r'\([^)]*\)', '', korean_name).strip()
                    english_name = re.sub(r'\([^)]*\)', '', english_name).strip()
                    # (as xxx) 형태 제거
                    english_name = re.sub(r'\s*\(as\s+[^)]+\)', '', english_name).strip()

                    return korean_name, english_name

            return None

        except Exception as e:
            logger.warning(f"API 호출 실패 ({product_name}): {e}")
            return None

    def process_single_ingredient(self, code, standard_row, ingredient_df):
        """단일 성분 처리 (전문의약품만, 주사제형 제외)"""
        ingredient_entries = ingredient_df[ingredient_df['일반명코드'] == code]

        if ingredient_entries.empty:
            # 주성분 정보가 없는 경우 API로 조회
            if self.api_key and pd.notna(standard_row['표준코드']):
                logger.info(f"주성분 정보 없음 - API로 조회: {code} (표준코드: {standard_row['표준코드']})")
                api_result = self.call_drug_api(standard_row['표준코드'])
                if api_result and (api_result[0] or api_result[1]):  # 한글명 또는 영문명이 있으면
                    korean_name = api_result[0] if api_result[0] else ''
                    english_name = api_result[1] if api_result[1] else ''

                    logger.info(f"API에서 성분명 찾음: {korean_name} / {english_name}")

                    # 표준코드에서 함량 정보 추출
                    density, unit = self.parse_dosage_info(standard_row['약품규격'])

                    return {
                        'ingr_code': code,
                        'atc_code': str(standard_row['ATC코드']) if pd.notna(standard_row['ATC코드']) else '',
                        'main_ingr_name_kr': korean_name,
                        'main_ingr_name_en': english_name,
                        'density': Decimal(str(density)),
                        'unit': unit,
                        'is_combination_drug': False,
                        'combination_group': '',
                    }

            logger.warning(f"성분 정보를 찾을 수 없음: {code}")
            return None

        # 첫 번째 항목 사용
        ingredient_row = ingredient_entries.iloc[0]

        # 표준코드에서 함량 정보 추출
        density, unit = self.parse_dosage_info(standard_row['약품규격'])

        # 성분 파일에서 함량 정보가 있으면 사용
        if pd.notna(ingredient_row['함량']) and ingredient_row['함량'] != 0:
            density = float(ingredient_row['함량'])
            if pd.notna(ingredient_row['단위']):
                unit = self.unit_mapping.get(str(ingredient_row['단위']).strip(), str(ingredient_row['단위']).strip())

        # 성분명 추출
        korean_name, english_name = self.extract_korean_english_names(
            ingredient_row['일반명'],
            standard_row['상품명'],
            standard_row['표준코드']
        )

        return {
            'ingr_code': code,
            'atc_code': str(standard_row['ATC코드']) if pd.notna(standard_row['ATC코드']) else '',
            'main_ingr_name_kr': korean_name,
            'main_ingr_name_en': english_name,
            'density': Decimal(str(density)),
            'unit': unit,
            'is_combination_drug': False,
            'combination_group': '',
        }

    def process_combination_drug(self, code, standard_row, ingredient_df):
        """복합제 처리 (전문의약품만, 주사제형 제외)"""
        ingredient_entries = ingredient_df[ingredient_df['일반명코드'] == code]
        combination_group = self.generate_combination_group(code)

        ingredients = []

        # 첫 번째 성분에 대해서만 API 호출 시도
        first_ingredient_row = ingredient_entries.iloc[0]
        api_korean_name = None
        api_english_name = None

        # 영문명이 있지만 한글명이 없는 경우 API로 한글명 검색
        first_korean, first_english = self.extract_korean_english_names(first_ingredient_row['일반명'])
        if (first_english and not first_korean) or (not first_english and not first_korean):
            if pd.notna(standard_row['표준코드']) and self.api_key:
                logger.debug(f"복합제 API 검색: {first_english} (표준코드: {standard_row['표준코드']})")
                api_result = self.call_drug_api(standard_row['표준코드'])
                if api_result:
                    if api_result[0]:
                        api_korean_name = api_result[0]
                    if api_result[1]:
                        api_english_name = api_result[1]
                    logger.info(f"복합제 API에서 성분명 찾음: {api_korean_name} / {api_english_name}")
                    time.sleep(0.5)

        for idx, (_, ingredient_row) in enumerate(ingredient_entries.iterrows()):
            # 함량 정보
            density = float(ingredient_row['함량']) if pd.notna(ingredient_row['함량']) else 0
            unit = self.unit_mapping.get(str(ingredient_row['단위']).strip(),
                                         str(ingredient_row['단위']).strip()) if pd.notna(ingredient_row['단위']) else 'mg'

            # 성분명
            korean_name, english_name = self.extract_korean_english_names(ingredient_row['일반명'])

            # 첫 번째 성분이고 API에서 성분명을 찾았으면 사용
            if idx == 0:
                if api_korean_name:
                    korean_name = api_korean_name
                if api_english_name and not english_name:
                    english_name = api_english_name

            # 복합제의 각 성분별 고유 코드 생성
            component_code = f"{code}_{idx + 1:02d}"

            ingredient_data = {
                'ingr_code': component_code,
                'atc_code': str(standard_row['ATC코드']) if pd.notna(standard_row['ATC코드']) else '',
                'main_ingr_name_kr': korean_name,
                'main_ingr_name_en': english_name,
                'density': Decimal(str(density)),
                'unit': unit,
                'is_combination_drug': True,
                'combination_group': combination_group,
            }

            ingredients.append(ingredient_data)

        return ingredients

    def save_ingredient(self, ingredient_data):
        """주성분 정보 저장"""
        try:
            ingredient, created = MainIngredient.objects.update_or_create(
                ingr_code=ingredient_data['ingr_code'],
                defaults=ingredient_data
            )

            if created:
                self.stats['created'] += 1
                action = '생성'
            else:
                self.stats['updated'] += 1
                action = '업데이트'

            logger.debug(f"{action}: {ingredient_data['ingr_code']} - {ingredient_data['main_ingr_name_kr']}")
            return True

        except (IntegrityError, ValidationError) as e:
            self.stats['errors'] += 1
            error_msg = f"저장 오류 - {ingredient_data['ingr_code']}: {str(e)}"
            self.error_details.append(error_msg)
            logger.error(error_msg)
            return False

    def import_ingredients(self, standard_code_file, ingredient_file):
        """주성분 정보 임포트"""
        logger.info("MainIngredient 임포트 시작")

        # 데이터 로드
        standard_df = self.load_standard_code_data(standard_code_file)
        if standard_df is None:
            return False

        ingredient_df = self.load_ingredient_data(ingredient_file)
        if ingredient_df is None:
            return False

        self.stats['total_standard_codes'] = len(standard_df)

        # 각 일반명코드 처리
        for idx, row in standard_df.iterrows():
            code = str(row['일반명코드']).strip()

            if idx % 100 == 0:
                logger.info(f"처리 진행률: {idx}/{len(standard_df)} ({idx / len(standard_df) * 100:.1f}%)")

            try:
                # 복합제 여부 확인
                is_combination = self.is_combination_drug_code(ingredient_df, code)

                if is_combination:
                    # 복합제 처리
                    ingredients_data = self.process_combination_drug(code, row, ingredient_df)
                    if ingredients_data:
                        self.stats['combination_drugs'] += 1
                        with transaction.atomic():
                            for ingredient_data in ingredients_data:
                                self.save_ingredient(ingredient_data)
                else:
                    # 단일 성분 처리
                    ingredient_data = self.process_single_ingredient(code, row, ingredient_df)
                    if ingredient_data:
                        self.stats['single_ingredients'] += 1
                        self.save_ingredient(ingredient_data)

                self.stats['valid_codes'] += 1

            except Exception as e:
                self.stats['errors'] += 1
                error_msg = f"처리 오류 - {code}: {str(e)}"
                self.error_details.append(error_msg)
                logger.error(error_msg)

        logger.info("MainIngredient 임포트 완료")
        return True

    def print_summary(self):
        """처리 결과 요약"""
        logger.info("=" * 60)
        logger.info("MainIngredient 임포트 결과 요약 (전문의약품만, 주사제형 제외)")
        logger.info("=" * 60)
        logger.info(f"총 표준코드 수: {self.stats['total_standard_codes']:,}")
        logger.info(f"유효한 코드 수: {self.stats['valid_codes']:,}")
        logger.info(f"단일 성분: {self.stats['single_ingredients']:,}")
        logger.info(f"복합제: {self.stats['combination_drugs']:,}")
        logger.info(f"생성된 레코드: {self.stats['created']:,}")
        logger.info(f"업데이트된 레코드: {self.stats['updated']:,}")
        logger.info(f"오류 발생: {self.stats['errors']:,}")

        if self.api_key:
            logger.info(f"API 호출 수: {self.stats['api_calls']:,}")
            logger.info(f"API 성공 수: {self.stats['api_success']:,}")
            if self.stats['api_calls'] > 0:
                success_rate = (self.stats['api_success'] / self.stats['api_calls']) * 100
                logger.info(f"API 성공률: {success_rate:.2f}%")

        # 성공률 계산
        if self.stats['total_standard_codes'] > 0:
            processing_rate = (self.stats['valid_codes'] / self.stats['total_standard_codes']) * 100
            logger.info(f"처리 성공률: {processing_rate:.2f}%")

        # 필터링 효과 확인
        try:
            total_count = MainIngredient.objects.count()
            prescription_only = MainIngredient.objects.exclude(atc_code='').count()

            logger.info(f"\n현재 저장된 총 주성분 데이터: {total_count:,}개")
            logger.info(f"ATC 코드 보유 (전문의약품): {prescription_only:,}개")
            logger.info("✅ 일반의약품 및 주사제형 제외 완료")
        except Exception as e:
            logger.warning(f"최종 통계 계산 실패: {e}")

        # 오류 상세 내용 (최대 10개)
        if self.error_details:
            logger.info(f"\n주요 오류 내용 (총 {len(self.error_details)}개 중 최대 10개):")
            for error in self.error_details[:10]:
                logger.info(f"  - {error}")


def validate_prescription_only():
    """전문의약품만 수집되었는지 검증"""
    logger.info("=== 전문의약품 필터링 검증 ===")

    # ATC 코드가 있는 성분들 (전문의약품 지표)
    with_atc = MainIngredient.objects.exclude(atc_code='').count()
    total = MainIngredient.objects.count()

    logger.info(f"총 주성분: {total:,}개")
    logger.info(f"ATC 코드 보유: {with_atc:,}개")

    if total > 0:
        atc_rate = (with_atc / total) * 100
        logger.info(f"ATC 코드 보유율: {atc_rate:.2f}%")

    # 한글명이 API로 보완된 성분들 확인
    korean_enhanced = MainIngredient.objects.filter(
        main_ingr_name_kr__isnull=False,
        main_ingr_name_en__isnull=False
    ).exclude(
        main_ingr_name_kr='',
        main_ingr_name_en=''
    ).count()

    logger.info(f"한글명+영문명 모두 보유: {korean_enhanced:,}개")


def find_api_enhanced_ingredients():
    """API로 한글명이 보완된 성분들 찾기"""
    logger.info("=== API로 한글명이 보완된 성분들 ===")

    # 영문명은 있지만 한글명이 새로 추가된 것으로 추정되는 성분들
    enhanced_ingredients = MainIngredient.objects.filter(
        main_ingr_name_en__isnull=False,
        main_ingr_name_kr__isnull=False
    ).exclude(
        main_ingr_name_en='',
        main_ingr_name_kr=''
    )[:20]  # 상위 20개만

    logger.info(f"영문명+한글명 보유 성분 예시 (상위 20개):")
    for ingredient in enhanced_ingredients:
        logger.info(f"  - {ingredient.ingr_code}: {ingredient.main_ingr_name_kr} / {ingredient.main_ingr_name_en}")


def check_injection_exclusion():
    """주사제형 제외 확인"""
    logger.info("=== 주사제형 제외 확인 ===")

    # 성분명에 주사 관련 키워드가 있는지 확인
    injection_keywords = ['주사', 'injection', '인젝션', '바이알', 'vial']

    for keyword in injection_keywords:
        count_kr = MainIngredient.objects.filter(
            main_ingr_name_kr__icontains=keyword
        ).count()
        count_en = MainIngredient.objects.filter(
            main_ingr_name_en__icontains=keyword
        ).count()

        if count_kr > 0 or count_en > 0:
            logger.warning(f"'{keyword}' 포함 성분 발견: 한글 {count_kr}개, 영문 {count_en}개")
        else:
            logger.info(f"'{keyword}' 포함 성분 없음 ✅")


def analyze_prescription_drugs():
    """전문의약품 분석"""
    logger.info("=== 전문의약품 분석 ===")

    # ATC 코드별 분포 (상위 10개)
    from django.db.models import Count

    atc_stats = MainIngredient.objects.exclude(atc_code='').values(
        'atc_code'
    ).annotate(
        count=Count('atc_code')
    ).order_by('-count')[:10]

    logger.info("ATC 코드별 분포 (상위 10개):")
    for stat in atc_stats:
        logger.info(f"  - {stat['atc_code']}: {stat['count']}개")

    # 복합제 중 전문의약품 비율
    total_combinations = MainIngredient.objects.filter(is_combination_drug=True).count()
    prescription_combinations = MainIngredient.objects.filter(
        is_combination_drug=True
    ).exclude(atc_code='').count()

    if total_combinations > 0:
        prescription_rate = (prescription_combinations / total_combinations) * 100
        logger.info(f"\n복합제 중 전문의약품: {prescription_combinations}/{total_combinations} ({prescription_rate:.1f}%)")


def main():
    """메인 실행 함수"""
    import argparse

    parser = argparse.ArgumentParser(description='MainIngredient 테이블 임포트 스크립트')
    parser.add_argument('--standard-code-file', type=str, required=True,
                        help='의약품표준코드 엑셀 파일 경로')
    parser.add_argument('--ingredient-file', type=str, required=True,
                        help='의약품주성분 엑셀 파일 경로')
    parser.add_argument('--api-key', type=str,
                        help='복합제 정보 조회용 API 키 (선택사항)')
    parser.add_argument('--clear-existing', action='store_true',
                        help='기존 데이터 삭제 후 새로 생성')

    args = parser.parse_args()

    # 파일 존재 확인
    if not os.path.exists(args.standard_code_file):
        logger.error(f"의약품표준코드 파일을 찾을 수 없습니다: {args.standard_code_file}")
        sys.exit(1)

    if not os.path.exists(args.ingredient_file):
        logger.error(f"의약품주성분 파일을 찾을 수 없습니다: {args.ingredient_file}")
        sys.exit(1)

    # 임포터 생성
    importer = MainIngredientImporter(args.api_key)

    # 기존 데이터 삭제 옵션
    if args.clear_existing:
        logger.info("기존 MainIngredient 데이터를 삭제합니다...")
        deleted_count = MainIngredient.objects.count()
        MainIngredient.objects.all().delete()
        logger.info(f"{deleted_count:,}개 레코드 삭제됨")

    # 기존 데이터 수 확인
    existing_count = MainIngredient.objects.count()
    logger.info(f"기존 주성분 데이터 수: {existing_count:,}")

    # 임포트 실행
    try:
        success = importer.import_ingredients(
            args.standard_code_file,
            args.ingredient_file
        )

        # 결과 요약 출력
        importer.print_summary()

        if success:
            # 최종 데이터 수 확인
            final_count = MainIngredient.objects.count()
            logger.info(f"최종 주성분 데이터 수: {final_count:,}")
            logger.info(f"증가한 데이터 수: {final_count - existing_count:,}")
            logger.info("✅ 임포트가 성공적으로 완료되었습니다!")
        else:
            logger.error("❌ 임포트 실패")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단되었습니다.")
        importer.print_summary()
        sys.exit(1)
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        sys.exit(1)


# 데이터 검증 및 분석 함수들
def analyze_imported_data():
    """임포트된 데이터 분석"""
    logger.info("=== 임포트된 데이터 분석 ===")

    # 기본 통계
    total_count = MainIngredient.objects.count()
    combination_count = MainIngredient.objects.filter(is_combination_drug=True).count()
    single_count = MainIngredient.objects.filter(is_combination_drug=False).count()

    logger.info(f"총 주성분: {total_count:,}개")
    logger.info(f"복합제 성분: {combination_count:,}개")
    logger.info(f"단일 성분: {single_count:,}개")

    # 복합제 그룹 분석
    from django.db.models import Count
    combination_groups = MainIngredient.objects.filter(
        is_combination_drug=True
    ).values('combination_group').annotate(
        count=Count('combination_group')
    ).order_by('-count')

    logger.info(f"복합제 그룹 수: {len(combination_groups)}개")

    if combination_groups:
        logger.info("복합제 그룹 상위 10개:")
        for group in combination_groups[:10]:
            group_ingredients = MainIngredient.objects.filter(
                combination_group=group['combination_group']
            )
            names = [ing.main_ingr_name_kr or ing.main_ingr_name_en for ing in group_ingredients]
            logger.info(f"  - {group['combination_group']}: {group['count']}개 성분 ({', '.join(names)})")

    # 단위별 분포
    unit_distribution = MainIngredient.objects.values('unit').annotate(
        count=Count('unit')
    ).order_by('-count')

    logger.info("단위별 분포 (상위 10개):")
    for unit_data in unit_distribution[:10]:
        logger.info(f"  - {unit_data['unit'] or '단위없음'}: {unit_data['count']}개")

    # 이름이 없는 데이터 확인
    no_korean_name = MainIngredient.objects.filter(main_ingr_name_kr='').count()
    no_english_name = MainIngredient.objects.filter(main_ingr_name_en='').count()
    no_names = MainIngredient.objects.filter(main_ingr_name_kr='', main_ingr_name_en='').count()

    logger.info(f"한글명 없음: {no_korean_name}개")
    logger.info(f"영문명 없음: {no_english_name}개")
    logger.info(f"한글명/영문명 모두 없음: {no_names}개")


def find_ingredient_by_name(name):
    """성분명으로 검색"""
    ingredients = MainIngredient.objects.filter(
        models.Q(main_ingr_name_kr__icontains=name) |
        models.Q(main_ingr_name_en__icontains=name)
    )

    logger.info(f"'{name}' 검색 결과: {ingredients.count()}개")

    for ingredient in ingredients[:10]:  # 상위 10개만 표시
        combination_info = ""
        if ingredient.is_combination_drug:
            combination_info = f" (복합제: {ingredient.combination_group})"

        logger.info(f"  - {ingredient.ingr_code}: {ingredient.main_ingr_name_kr} / {ingredient.main_ingr_name_en} "
                    f"[{ingredient.density}{ingredient.unit}]{combination_info}")


def validate_combination_groups():
    """복합제 그룹 검증"""
    logger.info("=== 복합제 그룹 검증 ===")

    # 모든 복합제 그룹 확인
    combination_groups = MainIngredient.objects.filter(
        is_combination_drug=True
    ).values_list('combination_group', flat=True).distinct()

    logger.info(f"총 복합제 그룹: {len(combination_groups)}개")

    for group in list(combination_groups)[:5]:  # 상위 5개 그룹만 확인
        ingredients = MainIngredient.objects.filter(combination_group=group)
        logger.info(f"\n그룹: {group} ({ingredients.count()}개 성분)")

        for ingredient in ingredients:
            logger.info(f"  - {ingredient.ingr_code}: {ingredient.main_ingr_name_kr} "
                        f"[{ingredient.density}{ingredient.unit}]")


if __name__ == "__main__":
    main()

# 사용 예시:
"""
# 기본 실행
python import_main_ingredients.py --standard-code-file "의약품표준코드2.xlsx" --ingredient-file "의약품주성분csv.xlsx"
python common/scripts/import_main_ingredients.py --standard-code-file "common/data/의약품표준코드2.xlsx" --ingredient-file "common/data/의약품주성분csv.xlsx" --api-key %2Bbcu3KBpBKHn0BE4HiPANIoA27EbfZuLmewRjN3bBDwKW0W1CEDIOhCaN3FJyWghf%2BGqpEziBNcZF%2F3LAWO7mw%3D%3D

# API 키와 함께 실행 (복합제 정보 조회)
python import_main_ingredients.py --standard-code-file "의약품표준코드2.xlsx" --ingredient-file "의약품주성분csv.xlsx" --api-key YOUR_API_KEY

# 기존 데이터 삭제 후 새로 생성
python import_main_ingredients.py --standard-code-file "의약품표준코드2.xlsx" --ingredient-file "의약품주성분csv.xlsx" --clear-existing

# Django shell에서 분석
python manage.py shell
>>> from import_main_ingredients import analyze_imported_data, find_ingredient_by_name, validate_combination_groups
>>> analyze_imported_data()
>>> find_ingredient_by_name('플루옥세틴')
>>> validate_combination_groups()
"""