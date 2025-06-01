# bokyak/views/medication_alert.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from bokyak.models.medication_alert import MedicationAlert
from bokyak.serializers import MedicationAlertSerializer


class MedicationAlertViewSet(viewsets.ModelViewSet):
    serializer_class = MedicationAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationAlert.objects.filter(
            medication_detail__cycle__group__medical_info__user=self.request.user
        ).select_related('medication_detail__medication')

    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """활성 알림 목록"""
        active_alerts = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_alerts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def upcoming_alerts(self, request):
        """다가오는 알림들 (1시간 내)"""
        now = timezone.now().time()
        one_hour_later = (timezone.now() + timedelta(hours=1)).time()

        upcoming = self.get_queryset().filter(
            is_active=True,
            alert_time__gte=now,
            alert_time__lte=one_hour_later
        )

        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)