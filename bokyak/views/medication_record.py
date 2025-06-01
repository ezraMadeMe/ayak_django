# bokyak/views/medication_record.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from bokyak.models.medication_record import MedicationRecord, MedicationDetail
from bokyak.serializers import MedicationRecordSerializer, CreateMedicationRecordSerializer


class MedicationRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user=self.request.user
        ).select_related('medication_detail__medication')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMedicationRecordSerializer
        return MedicationRecordSerializer

    @action(detail=False, methods=['get'])
    def today_records(self, request):
        """오늘의 복약 기록"""
        today = timezone.now().date()
        today_records = self.get_queryset().filter(
            record_date__date=today
        ).order_by('-record_date')

        serializer = self.get_serializer(today_records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """복약 통계"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now().date() - timedelta(days=days)

        records = self.get_queryset().filter(record_date__date__gte=start_date)

        total_records = records.count()
        taken_records = records.filter(record_type=MedicationRecord.RecordType.TAKEN).count()
        missed_records = records.filter(record_type=MedicationRecord.RecordType.MISSED).count()

        compliance_rate = (taken_records / total_records * 100) if total_records > 0 else 0

        data = {
            'period_days': days,
            'total_records': total_records,
            'taken_records': taken_records,
            'missed_records': missed_records,
            'compliance_rate': round(compliance_rate, 2)
        }
        return Response(data)

    @action(detail=False, methods=['post'])
    def bulk_record(self, request):
        """여러 약물 한번에 복용 기록"""
        medication_details = request.data.get('medication_details', [])
        record_type = request.data.get('record_type', MedicationRecord.RecordType.TAKEN)
        record_date = request.data.get('record_date', timezone.now())
        notes = request.data.get('notes', '')

        created_records = []
        for detail_data in medication_details:
            detail_id = detail_data.get('medication_detail_id')
            quantity = detail_data.get('quantity_taken', 1)

            try:
                medication_detail = MedicationDetail.objects.get(
                    id=detail_id,
                    cycle__group__medical_info__user=self.request.user
                )

                record = MedicationRecord.objects.create(
                    medication_detail=medication_detail,
                    record_type=record_type,
                    record_date=record_date,
                    quantity_taken=quantity,
                    notes=notes
                )

                # 복용 기록인 경우 잔여량 업데이트
                if record_type == MedicationRecord.RecordType.TAKEN:
                    medication_detail.remaining_quantity -= quantity
                    medication_detail.save()

                created_records.append(record)

            except MedicationDetail.DoesNotExist:
                continue

        serializer = MedicationRecordSerializer(created_records, many=True)
        return Response(serializer.data)