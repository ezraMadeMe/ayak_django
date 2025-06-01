# bokyak/views/prescription.py
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from bokyak.models.prescription_medication import Prescription, PrescriptionMedication
from bokyak.serializers import (
    PrescriptionSerializer, PrescriptionDetailSerializer, CreatePrescriptionSerializer
)
from bokyak.serializers.prescription import SharedPrescriptionSerializer
from user.models import UserMedicalInfo


class PrescriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prescription.objects.filter(
            medical_info__user=self.request.user
        ).select_related('medical_info__hospital', 'medical_info__illness')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePrescriptionSerializer
        elif self.action == 'retrieve':
            return PrescriptionDetailSerializer
        return PrescriptionSerializer

    @action(detail=False, methods=['get'])
    def active(self, request):
        """활성 처방전 목록"""
        active_prescriptions = self.get_queryset().filter(is_active=True)
        serializer = PrescriptionSerializer(active_prescriptions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_prescription(self, request, pk=None):
        """처방전 갱신"""
        prescription = self.get_object()

        # 새 처방전 데이터
        new_data = {
            'medical_info': prescription.medical_info,
            'prescription_date': request.data.get('prescription_date', timezone.now().date())
        }

        new_prescription = prescription.update_prescription(new_data)

        # 새 처방 의약품들 생성
        medications_data = request.data.get('medications', [])
        for medication_data in medications_data:
            PrescriptionMedication.objects.create(
                prescription=new_prescription,
                **medication_data
            )

        serializer = PrescriptionDetailSerializer(new_prescription)
        return Response(serializer.data)


class PrescriptionViewSet(viewsets.ModelViewSet):

    @action(detail=False, methods=['post'])
    def create_shared_prescription(self, request):
        """여러 질병을 위한 공유 처방전 생성"""
        data = request.data

        with transaction.atomic():
            # 1. 처방전 생성
            prescription = Prescription.objects.create(
                prescription_date=data['prescription_date']
            )

            # 2. 의료정보들과 연결
            for medical_info_id in data['medical_info_ids']:
                medical_info = UserMedicalInfo.objects.get(
                    id=medical_info_id,
                    user=request.user
                )
                medical_info.prescription = prescription
                medical_info.save()

            # 3. 처방 의약품 추가
            for med_data in data['medications']:
                PrescriptionMedication.objects.create(
                    prescription=prescription,
                    **med_data
                )

        serializer = SharedPrescriptionSerializer(prescription)
        return Response(serializer.data)