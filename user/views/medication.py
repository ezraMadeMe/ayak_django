# user/views/medication.py
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from user.models.medication import MainIngredient, Medication
from user.services.medication_service import MedicationService
from user.formatters import format_api_response


class MainIngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainIngredient.objects.filter(is_combination_drug=True)

    def get_ingredient_data(self, ingredient):
        return {
            'ingr_code': ingredient.ingr_code,
            'atc_code': ingredient.atc_code,
            'main_ingr_name_kr': ingredient.main_ingr_name_kr,
            'main_ingr_name_en': ingredient.main_ingr_name_en,
            'density': ingredient.density,
            'unit': ingredient.unit,
            'is_combination_drug': ingredient.is_combination_drug,
            'combination_group': ingredient.combination_group,
            'created_at': ingredient.created_at.isoformat() if ingredient.created_at else None,
            'updated_at': ingredient.updated_at.isoformat() if ingredient.updated_at else None,
        }

    def list(self, request):
        ingredients = self.get_queryset()
        data = [self.get_ingredient_data(ingredient) for ingredient in ingredients]
        return Response(data)

    def retrieve(self, request, pk=None):
        ingredient = self.get_object()
        data = self.get_ingredient_data(ingredient)
        return Response(data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """성분명으로 검색"""
        name = request.query_params.get('name')
        if not name:
            return Response({'error': '검색어를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        ingredients = MainIngredient.search_by_name(name)[:20]
        data = [self.get_ingredient_data(ingredient) for ingredient in ingredients]
        return Response(data)

    @action(detail=True, methods=['get'])
    def combinations(self, request, pk=None):
        """복합제 성분들 조회"""
        ingredient = self.get_object()
        combinations = ingredient.get_related_combinations()
        data = [self.get_ingredient_data(combination) for combination in combinations]
        return Response(data)


class MedicationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Medication.objects.all()

    def get_medication_data(self, medication):
        return {
            'id': medication.id,
            'item_name': medication.item_name,
            'item_seq': medication.item_seq,
            'entp_name': medication.entp_name,
            'chart': medication.chart,
            'class_no': medication.class_no,
            'class_name': medication.class_name,
            'etc_otc_code': medication.etc_otc_code,
            'etc_otc_name': medication.etc_otc_name,
            'created_at': medication.created_at.isoformat() if medication.created_at else None,
            'updated_at': medication.updated_at.isoformat() if medication.updated_at else None,
            'ingredient_details': [
                {
                    'id': detail.id,
                    'ingredient': {
                        'id': detail.ingredient.id,
                        'name': detail.ingredient.name,
                        'english_name': detail.ingredient.english_name,
                        'code': detail.ingredient.code
                    },
                    'unit': detail.unit,
                    'amount': detail.amount
                } for detail in medication.ingredient_details.select_related('ingredient').all()
            ]
        }

    def list(self, request):
        medications = self.get_queryset()
        data = [self.get_medication_data(medication) for medication in medications]
        return Response(data)

    def retrieve(self, request, pk=None):
        medication = self.get_object()
        data = self.get_medication_data(medication)
        return Response(data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """의약품명으로 검색"""
        name = request.query_params.get('name')
        if not name:
            return Response({'error': '검색어를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        medications = Medication.objects.filter(
            item_name__icontains=name
        ).prefetch_related('ingredient_details__ingredient')[:20]

        data = [self.get_medication_data(medication) for medication in medications]
        return Response(data)


@api_view(['GET'])
def search_medications(request):
    """약물 검색 API"""
    try:
        keyword = request.GET.get('keyword')
        class_name = request.GET.get('class_name')
        drug_form = request.GET.get('drug_form')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        result = MedicationService.search_medications(
            keyword=keyword,
            limit=limit,
            offset=offset
        )

        return Response(format_api_response(
            success=True,
            data=result,
            message='약물 검색 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 검색 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_medication_detail(request, item_seq):
    """약물 상세 정보 조회 API"""
    try:
        medication_data = MedicationService.get_medication_detail(item_seq)

        return Response(format_api_response(
            success=True,
            data=medication_data,
            message='약물 상세 정보 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 상세 정보 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_medication_classes(request):
    """약물 분류 목록 조회 API"""
    try:
        classes = MedicationService.get_medication_classes()

        return Response(format_api_response(
            success=True,
            data=classes,
            message='약물 분류 목록 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 분류 목록 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_drug_forms(request):
    """제형 목록 조회 API"""
    try:
        forms = MedicationService.get_drug_forms()

        return Response(format_api_response(
            success=True,
            data=forms,
            message='제형 목록 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'제형 목록 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def search_by_name(request):
    """약물명으로 검색 API"""
    try:
        name = request.GET.get('name')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        if not name:
            return Response(format_api_response(
                success=False,
                message='약물명을 입력해주세요.'
            ), status=status.HTTP_400_BAD_REQUEST)

        result = MedicationService.search_by_name(
            name=name,
            limit=limit,
            offset=offset
        )

        return Response(format_api_response(
            success=True,
            data=result,
            message='약물명으로 검색 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 검색 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_medications_by_class(request, class_name):
    """분류별 약물 목록 조회 API"""
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        result = MedicationService.get_medications_by_class(
            class_name=class_name,
            limit=limit,
            offset=offset
        )

        return Response(format_api_response(
            success=True,
            data=result,
            message='분류별 약물 목록 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 목록 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_medications_by_form(request, drug_form):
    """제형별 약물 목록 조회 API"""
    try:
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        result = MedicationService.get_medications_by_form(
            drug_form=drug_form,
            limit=limit,
            offset=offset
        )

        return Response(format_api_response(
            success=True,
            data=result,
            message='제형별 약물 목록 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 목록 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def search_by_mark_code(request):
    """식별 표시로 약물 검색 API"""
    try:
        mark_code = request.GET.get('mark_code')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        if not mark_code:
            return Response(format_api_response(
                success=False,
                message='식별 표시를 입력해주세요.'
            ), status=status.HTTP_400_BAD_REQUEST)

        result = MedicationService.search_by_mark_code(
            mark_code=mark_code,
            limit=limit,
            offset=offset
        )

        return Response(format_api_response(
            success=True,
            data=result,
            message='식별 표시로 약물 검색 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 검색 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def search_by_shape(request):
    """모양과 색상으로 약물 검색 API"""
    try:
        color = request.GET.get('color')
        drug_shape = request.GET.get('drug_shape')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))

        if not color and not drug_shape:
            return Response(format_api_response(
                success=False,
                message='색상 또는 모양을 입력해주세요.'
            ), status=status.HTTP_400_BAD_REQUEST)

        result = MedicationService.search_by_shape(
            color=color,
            drug_shape=drug_shape,
            limit=limit,
            offset=offset
        )

        return Response(format_api_response(
            success=True,
            data=result,
            message='모양과 색상으로 약물 검색 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'약물 검색 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
