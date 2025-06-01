# bokyak/views/medication_detail.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from bokyak.models.medication_detail import MedicationDetail
from bokyak.serializers import MedicationDetailSerializer, MedicationDetailWithRecordsSerializer


class MedicationDetailViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationDetail.objects.filter(
            cycle__group__medical_info__user=self.request.user
        ).select_related('cycle__group', 'medication')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MedicationDetailWithRecordsSerializer
        return MedicationDetailSerializer

    @action(detail=False, methods=['get'])
    def today_medications(self, request):
        """오늘 복용해야 할 약물들"""
        today = timezone.now().date()

        # 활성 상태이고 잔여량이 있는 약물들
        medications = self.get_queryset().filter(
            is_active=True,
            remaining_quantity__gt=0,
            cycle__is_active=True
        )

        serializer = MedicationDetailSerializer(medications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """잔여량 부족 약물들 (5일치 이하)"""
        low_stock_medications = self.get_queryset().filter(
            is_active=True,
            remaining_quantity__lte=5,
            cycle__is_active=True
        )

        serializer = MedicationDetailSerializer(low_stock_medications, many=True)
        return Response(serializer.data)