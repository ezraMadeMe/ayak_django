# bokyak/views/medication_detail.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from bokyak.models.medication_detail import MedicationDetail


class MedicationDetailViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationDetail.objects.filter(
            cycle__group__medical_info__user=self.request.user
        ).select_related('cycle__group', 'medication')

    def get_medication_detail_data(self, detail, include_records=False):
        data = {
            'id': detail.id,
            'medication': {
                'id': detail.medication.id,
                'item_name': detail.medication.item_name,
                'item_seq': detail.medication.item_seq,
                'entp_name': detail.medication.entp_name
            },
            'cycle': {
                'id': detail.cycle.id,
                'group': {
                    'id': detail.cycle.group.id,
                    'name': detail.cycle.group.name
                },
                'start_date': detail.cycle.start_date.isoformat() if detail.cycle.start_date else None,
                'end_date': detail.cycle.end_date.isoformat() if detail.cycle.end_date else None,
                'is_active': detail.cycle.is_active
            },
            'dosage': detail.dosage,
            'dosage_unit': detail.dosage_unit,
            'times_per_day': detail.times_per_day,
            'days': detail.days,
            'usage_instructions': detail.usage_instructions,
            'remaining_quantity': detail.remaining_quantity,
            'is_active': detail.is_active,
            'created_at': detail.created_at.isoformat() if detail.created_at else None,
            'updated_at': detail.updated_at.isoformat() if detail.updated_at else None
        }

        if include_records:
            data['records'] = [
                {
                    'id': record.id,
                    'record_type': record.record_type,
                    'quantity_taken': record.quantity_taken,
                    'notes': record.notes,
                    'record_date': record.record_date.isoformat() if record.record_date else None,
                    'created_at': record.created_at.isoformat() if record.created_at else None
                }
                for record in detail.records.all().order_by('-record_date', '-created_at')
            ]

        return data

    def list(self, request):
        details = self.get_queryset()
        data = [self.get_medication_detail_data(detail) for detail in details]
        return Response(data)

    def retrieve(self, request, pk=None):
        detail = self.get_object()
        data = self.get_medication_detail_data(detail, include_records=True)
        return Response(data)

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

        data = [self.get_medication_detail_data(medication) for medication in medications]
        return Response({
            'success': True,
            'data': data,
            'message': '오늘의 복용 약물 조회 성공'
        })

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """잔여량 부족 약물들 (5일치 이하)"""
        low_stock_medications = self.get_queryset().filter(
            is_active=True,
            remaining_quantity__lte=5,
            cycle__is_active=True
        )

        data = [self.get_medication_detail_data(medication) for medication in low_stock_medications]
        return Response({
            'success': True,
            'data': data,
            'message': '잔여량 부족 약물 조회 성공'
        })