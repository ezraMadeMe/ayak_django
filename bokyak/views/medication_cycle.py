# bokyak/views/medication_cycle.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from bokyak.models.medication_cycle import MedicationCycle
from bokyak.serializers import MedicationCycleSerializer, MedicationCycleDetailSerializer


class MedicationCycleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationCycle.objects.filter(
            group__medical_info__user=self.request.user
        ).select_related('group')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MedicationCycleDetailSerializer
        return MedicationCycleSerializer

    @action(detail=False, methods=['get'])
    def current_cycles(self, request):
        """현재 활성 주기들"""
        current_cycles = self.get_queryset().filter(is_active=True)
        serializer = MedicationCycleDetailSerializer(current_cycles, many=True)
        return Response(serializer.data)