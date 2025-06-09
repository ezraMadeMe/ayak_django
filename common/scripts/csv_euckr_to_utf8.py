# -*- coding: utf-8 -*-
import os
import sys

import django
import pandas as pd
import chardet

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

# DJANGO_SETTINGS_MODULE 환경 변수를 설정합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')

# Django를 설정합니다.
django.setup()

def detect_encoding(file_path):
    """파일의 인코딩을 자동 감지"""
    with open(file_path, 'rb') as f:
        raw_data = f.read()
        result = chardet.detect(raw_data)
        return result


def convert_csv_with_multiple_encodings():
    file_path = '../data/main_ingr.csv'

    # 1. 먼저 chardet으로 인코딩 감지
    print("파일 인코딩 자동 감지 중...")
    encoding_result = detect_encoding(file_path)
    print(f"감지된 인코딩: {encoding_result}")

    # 2. 시도할 인코딩 목록 (감지된 인코딩을 첫 번째로)
    encodings_to_try = []
    if encoding_result['encoding']:
        encodings_to_try.append(encoding_result['encoding'])

    # 추가 인코딩들
    additional_encodings = [
        'cp949', 'euc-kr', 'utf-8', 'utf-8-sig',
        'cp1252', 'latin-1', 'iso-8859-1', 'ascii'
    ]

    for enc in additional_encodings:
        if enc not in encodings_to_try:
            encodings_to_try.append(enc)

    # 3. 각 인코딩으로 시도
    for encoding in encodings_to_try:
        try:
            print(f"\n{encoding} 인코딩으로 시도 중...")
            df = pd.read_csv(file_path, encoding=encoding, low_memory=False)

            print(f"✓ 성공! {encoding} 인코딩으로 {len(df)} 행 읽음")
            print(f"컬럼명: {list(df.columns)}")

            # 첫 번째 행 확인
            if len(df) > 0:
                first_row = df.iloc[0]
                print(f"첫 번째 행 샘플:")
                for i, (col, val) in enumerate(first_row.items()):
                    print(f"  {i}: {col} = {val}")
                    if i >= 3:  # 처음 4개 컬럼만 표시
                        break

            # UTF-8로 저장
            output_file = '../data/main_ingr_utf8.csv'
            print(f"\nUTF-8로 변환하여 {output_file}에 저장 중...")
            df.to_csv(output_file, encoding='utf-8-sig', index=False)

            print("✓ 변환 완료!")
            print(f"사용된 원본 인코딩: {encoding}")
            print(f"변환된 파일: {output_file}")

            # 변환된 파일 검증
            print("\n변환된 파일 검증 중...")
            test_df = pd.read_csv(output_file, encoding='utf-8-sig')
            print(f"검증 결과: {len(test_df)} 행, 컬럼명: {list(test_df.columns)}")

            return True

        except UnicodeDecodeError as e:
            print(f"✗ {encoding} 실패: {e}")
            continue
        except Exception as e:
            print(f"✗ {encoding} 실패: {e}")
            continue

    print("\n모든 인코딩 시도 실패!")

    # 4. 마지막 시도: errors='ignore' 옵션 사용
    print("\n마지막 시도: 오류 문자 무시하고 읽기...")
    try:
        for encoding in ['cp949', 'euc-kr', 'latin-1']:
            try:
                print(f"{encoding} + errors='ignore' 시도...")
                df = pd.read_csv(file_path, encoding=encoding, errors='ignore', low_memory=False)

                print(f"✓ 부분 성공! {len(df)} 행 읽음 (일부 문자 손실 가능)")
                print(f"컬럼명: {list(df.columns)}")

                # UTF-8로 저장
                output_file = '../data/main_ingr_utf8_partial.csv'
                df.to_csv(output_file, encoding='utf-8-sig', index=False)
                print(f"저장 완료: {output_file}")
                return True

            except Exception as e:
                print(f"✗ {encoding} + ignore 실패: {e}")
                continue

    except Exception as e:
        print(f"최종 시도 실패: {e}")

    return False


if __name__ == "__main__":
    success = convert_csv_with_multiple_encodings()
    if not success:
        print("\nCSV 변환에 실패했습니다. 파일을 수동으로 확인해주세요.")