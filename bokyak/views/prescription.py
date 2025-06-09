# bokyak/views/prescription.py
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from bokyak.models.prescription_medication import Prescription, PrescriptionMedication
from user.models import UserMedicalInfo


class PrescriptionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prescription.objects.filter(
            medical_info__user=self.request.user
        ).select_related('medical_info__hospital', 'medical_info__illness')

    def get_prescription_data(self, prescription, include_medications=True):
        data = {
            'id': prescription.id,
            'medical_info': {
                'id': prescription.medical_info.id,
                'hospital': {
                    'hospital_id': prescription.medical_info.hospital.hospital_id,
                    'hosp_name': prescription.medical_info.hospital.hosp_name
                } if prescription.medical_info.hospital else None,
                'illness': {
                    'id': prescription.medical_info.illness.id,
                    'name': prescription.medical_info.illness.name
                } if prescription.medical_info.illness else None,
            },
            'prescription_date': prescription.prescription_date.isoformat() if prescription.prescription_date else None,
            'is_active': prescription.is_active,
            'created_at': prescription.created_at.isoformat() if prescription.created_at else None,
            'updated_at': prescription.updated_at.isoformat() if prescription.updated_at else None
        }

        if include_medications:
            data['medications'] = [
                {
                    'id': med.id,
                    'medication': {
                        'id': med.medication.id,
                        'item_name': med.medication.item_name,
                        'item_seq': med.medication.item_seq
                    },
                    'dosage': med.dosage,
                    'dosage_unit': med.dosage_unit,
                    'times_per_day': med.times_per_day,
                    'days': med.days,
                    'usage_instructions': med.usage_instructions
                }
                for med in prescription.prescription_medications.select_related('medication').all()
            ]

        return data

    def list(self, request):
        prescriptions = self.get_queryset()
        data = [self.get_prescription_data(prescription) for prescription in prescriptions]
        return Response(data)

    def retrieve(self, request, pk=None):
        prescription = self.get_object()
        data = self.get_prescription_data(prescription, include_medications=True)
        return Response(data)

    def create(self, request):
        try:
            # 필수 필드 검증
            required_fields = ['medical_info_id', 'prescription_date', 'medications']
            for field in required_fields:
                if field not in request.data:
                    return Response({
                        'success': False,
                        'message': f'{field}는 필수 입력 항목입니다.'
                    }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # 의료 정보 조회
                medical_info = UserMedicalInfo.objects.get(
                    id=request.data['medical_info_id'],
                    user=request.user
                )

                # 처방전 생성
                prescription = Prescription.objects.create(
                    medical_info=medical_info,
                    prescription_date=request.data['prescription_date']
                )

                # 처방 의약품 생성
                for med_data in request.data['medications']:
                    PrescriptionMedication.objects.create(
                        prescription=prescription,
                        **med_data
                    )

            data = self.get_prescription_data(prescription)
            return Response({
                'success': True,
                'data': data,
                'message': '처방전이 성공적으로 생성되었습니다.'
            }, status=status.HTTP_201_CREATED)

        except UserMedicalInfo.DoesNotExist:
            return Response({
                'success': False,
                'message': '해당하는 의료 정보를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'처방전 생성 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """활성 처방전 목록"""
        active_prescriptions = self.get_queryset().filter(is_active=True)
        data = [self.get_prescription_data(prescription) for prescription in active_prescriptions]
        return Response(data)

    @action(detail=True, methods=['post'])
    def update_prescription(self, request, pk=None):
        """처방전 갱신"""
        prescription = self.get_object()

        try:
            with transaction.atomic():
                # 새 처방전 생성
                new_prescription = Prescription.objects.create(
                    medical_info=prescription.medical_info,
                    prescription_date=request.data.get('prescription_date', timezone.now().date())
                )

                # 새 처방 의약품들 생성
                medications_data = request.data.get('medications', [])
                for medication_data in medications_data:
                    PrescriptionMedication.objects.create(
                        prescription=new_prescription,
                        **medication_data
                    )

                # 이전 처방전 비활성화
                prescription.is_active = False
                prescription.save()

            data = self.get_prescription_data(new_prescription)
            return Response({
                'success': True,
                'data': data,
                'message': '처방전이 성공적으로 갱신되었습니다.'
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'처방전 갱신 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def create_shared_prescription(self, request):
        """여러 질병을 위한 공유 처방전 생성"""
        try:
            data = request.data
            required_fields = ['prescription_date', 'medical_info_ids', 'medications']
            for field in required_fields:
                if field not in data:
                    return Response({
                        'success': False,
                        'message': f'{field}는 필수 입력 항목입니다.'
                    }, status=status.HTTP_400_BAD_REQUEST)

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

            data = self.get_prescription_data(prescription)
            return Response({
                'success': True,
                'data': data,
                'message': '공유 처방전이 성공적으로 생성되었습니다.'
            }, status=status.HTTP_201_CREATED)

        except UserMedicalInfo.DoesNotExist:
            return Response({
                'success': False,
                'message': '해당하는 의료 정보를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'공유 처방전 생성 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)