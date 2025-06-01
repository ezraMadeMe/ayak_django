# user/views/medication.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from user.models.medication import MainIngredient, Medication
from user.serializers import MainIngredientSerializer, MedicationSerializer


class MainIngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MainIngredient.objects.filter(is_active=True)
    serializer_class = MainIngredientSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        """성분명으로 검색"""
        name = request.query_params.get('name')
        if not name:
            return Response({'error': '검색어를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        ingredients = MainIngredient.search_by_name(name)[:20]
        serializer = self.get_serializer(ingredients, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def combinations(self, request, pk=None):
        """복합제 성분들 조회"""
        ingredient = self.get_object()
        combinations = ingredient.get_related_combinations()
        serializer = self.get_serializer(combinations, many=True)
        return Response(serializer.data)


class MedicationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Medication.objects.all()
    serializer_class = MedicationSerializer

    @action(detail=False, methods=['get'])
    def search(self, request):
        """의약품명으로 검색"""
        name = request.query_params.get('name')
        if not name:
            return Response({'error': '검색어를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        medications = Medication.objects.filter(
            item_name__icontains=name
        ).prefetch_related('ingredient_details__ingredient')[:20]

        serializer = self.get_serializer(medications, many=True)
        return Response(serializer.data)
