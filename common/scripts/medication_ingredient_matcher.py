import logging
import os
import sys
import django

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ayak.settings')
django.setup()


# 성분 매칭 및 관계 생성 스크립트
from decimal import Decimal

from django.db import models

from user.models.medication import Medication
from user.models.medication_ingredient import MedicationIngredient
from user.models.main_ingredient import MainIngredient


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

class MedicationIngredientMatcher:
    """의약품과 주성분을 매칭하여 관계를 생성하는 클래스"""

    def __init__(self):
        self.stats = {
            'total_medications': 0,
            'matched_medications': 0,
            'unmatched_medications': 0,
            'relationships_created': 0,
            'errors': 0
        }
        self.error_details = []

    def match_ingredients(self):
        """모든 의약품에 대해 주성분 매칭 수행"""
        from django.db import transaction

        medications = Medication.objects.filter()
        self.stats['total_medications'] = medications.count()

        for medication in medications:
            try:
                with transaction.atomic():
                    matched = self.match_medication_ingredients(medication)
                    if matched:
                        self.stats['matched_medications'] += 1
                    else:
                        self.stats['unmatched_medications'] += 1
            except Exception as e:
                self.stats['errors'] += 1
                self.error_details.append(f"오류 - {medication.medication_name}: {str(e)}")

    def match_medication_ingredients(self, medication):
        """개별 의약품의 주성분 매칭"""
        matched_count = 0

        # 1. search_ingredient로 직접 매칭
        if medication.ingredients.main_ingr_name_kr:
            ingredient = self.find_matching_ingredient(medication.ingredients.main_ingr_name_kr)
            if ingredient:
                self.create_medication_ingredient_relationship(medication, ingredient, medication.ingredients.main_ingr_name_kr)
                matched_count += 1

        # 2. active_ingredient로 매칭
        if medication.active_ingredient and not matched_count:
            ingredient = self.find_matching_ingredient(medication.active_ingredient)
            if ingredient:
                self.create_medication_ingredient_relationship(medication, ingredient, medication.active_ingredient)
                matched_count += 1

        # 3. material_name에서 성분 추출하여 매칭
        if medication.material_name and not matched_count:
            ingredients = self.extract_ingredients_from_material(medication.material_name)
            for ingredient_name, amount, unit in ingredients:
                ingredient = self.find_matching_ingredient(ingredient_name)
                if ingredient:
                    self.create_medication_ingredient_relationship(
                        medication, ingredient, ingredient_name, amount, unit
                    )
                    matched_count += 1

        return matched_count > 0

    def find_matching_ingredient(self, ingredient_name):
        """성분명으로 MainIngredient 찾기"""
        if not ingredient_name:
            return None

        # 정확히 일치하는 한글명 찾기
        ingredient = MainIngredient.objects.filter(
            main_ingr_name_kr__iexact=ingredient_name.strip()
        ).first()

        if ingredient:
            return ingredient

        # 영문명으로 찾기
        ingredient = MainIngredient.objects.filter(
            main_ingr_name_en__iexact=ingredient_name.strip()
        ).first()

        if ingredient:
            return ingredient

        # 부분 일치로 찾기
        ingredient = MainIngredient.objects.filter(
            main_ingr_name_kr__icontains=ingredient_name.strip()
        ).first()

        return ingredient

    def extract_ingredients_from_material(self, material_text):
        """원료성분 텍스트에서 성분 정보 추출"""
        import re

        ingredients = []
        if not material_text:
            return ingredients

        # 성분명(함량단위) 패턴 추출
        # 예: "플루옥세틴염산염(20mg)", "세르트랄린염산염(50mg)" 등
        pattern = r'([가-힣A-Za-z]+(?:염산염|황산염|구연산염)?)\s*\(?(\d+(?:\.\d+)?)\s*([a-zA-Z]+)\)?'
        matches = re.findall(pattern, material_text)

        for match in matches:
            ingredient_name = match[0].strip()
            amount = float(match[1]) if match[1] else 0
            unit = match[2].strip()
            ingredients.append((ingredient_name, amount, unit))

        return ingredients

    def create_medication_ingredient_relationship(self, medication, ingredient, source_name, amount=0, unit='mg'):
        """의약품-주성분 관계 생성"""
        try:
            relationship, created = MedicationIngredient.objects.get_or_create(
                medication=medication,
                main_ingredient=ingredient,
                defaults={
                    'amount': Decimal(str(amount)) if amount else Decimal('0'),
                    'unit': unit,
                    'is_main': True,
                    'ingredient_role': '주성분',
                    'notes': f'매칭 소스: {source_name}'
                }
            )

            if created:
                self.stats['relationships_created'] += 1
                print(f"✓ 관계 생성: {medication.medication_name} - {ingredient.main_ingr_name_kr}")

            return relationship

        except Exception as e:
            self.error_details.append(f"관계 생성 오류 - {medication.medication_name}: {str(e)}")
            return None

    def print_summary(self):
        """매칭 결과 요약"""
        print("=" * 50)
        print("의약품-주성분 매칭 완료")
        print("=" * 50)
        print(f"총 의약품 수: {self.stats['total_medications']:,}")
        print(f"매칭 성공: {self.stats['matched_medications']:,}")
        print(f"매칭 실패: {self.stats['unmatched_medications']:,}")
        print(f"생성된 관계: {self.stats['relationships_created']:,}")
        print(f"오류 발생: {self.stats['errors']:,}")

        if self.stats['total_medications'] > 0:
            success_rate = (self.stats['matched_medications'] / self.stats['total_medications']) * 100
            print(f"매칭 성공률: {success_rate:.2f}%")


# 사용 예시 스크립트
def run_ingredient_matching():
    """의약품-주성분 매칭 실행"""
    matcher = MedicationIngredientMatcher()

    print("의약품-주성분 매칭 시작...")
    matcher.match_ingredients()
    matcher.print_summary()

    # 매칭 결과 검증
    print("\n매칭 결과 검증:")

    # 복합제 확인
    combination_drugs = Medication.objects.annotate(
        ingredient_count=models.Count('ingredients', filter=models.Q(ingredients__is_active=True))
    ).filter(ingredient_count__gt=1)

    print(f"복합제로 식별된 의약품: {combination_drugs.count()}개")

    # 매칭되지 않은 의약품 확인
    unmatched = Medication.objects.annotate(
        ingredient_count=models.Count('ingredients')
    ).filter(ingredient_count=0)

    print(f"매칭되지 않은 의약품: {unmatched.count()}개")

    if unmatched.exists():
        print("매칭되지 않은 의약품 예시:")
        for med in unmatched[:5]:
            print(f"  - {med.medication_name} (검색성분: {med.ingredients.main_ingr_name_kr})")


if __name__ == "__main__":
    # Django 환경 설정 후 실행
    run_ingredient_matching()
