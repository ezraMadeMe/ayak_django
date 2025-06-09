# bokyak/views/medication_group.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from bokyak.models.medication_detail import MedicationDetail
from bokyak.models.medication_group import MedicationGroup

from user.models import UserMedicalInfo


class MedicationGroupViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationGroup.objects.filter(
            medical_info__user=self.request.user
        ).select_related('medical_info__hospital', 'medical_info__illness', 'prescription')

    def get_medication_group_data(self, group, include_details=False):
        data = {
            'id': group.id,
            'medical_info': {
                'id': group.medical_info.id,
                'hospital': {
                    'hospital_id': group.medical_info.hospital.hospital_id,
                    'hosp_name': group.medical_info.hospital.hosp_name
                } if group.medical_info.hospital else None,
                'illness': {
                    'id': group.medical_info.illness.id,
                    'name': group.medical_info.illness.name
                } if group.medical_info.illness else None
            },
            'prescription': {
                'id': group.prescription.id,
                'prescription_date': group.prescription.prescription_date.isoformat() if group.prescription.prescription_date else None,
                'is_active': group.prescription.is_active
            } if group.prescription else None,
            'group_name': group.group_name,
            'created_at': group.created_at.isoformat() if group.created_at else None,
            'updated_at': group.updated_at.isoformat() if group.updated_at else None
        }

        if include_details:
            data['cycles'] = []
            for cycle in group.cycles.all():
                cycle_data = {
                    'id': cycle.id,
                    'start_date': cycle.start_date.isoformat() if cycle.start_date else None,
                    'end_date': cycle.end_date.isoformat() if cycle.end_date else None,
                    'is_active': cycle.is_active,
                    'medication_details': []
                }
                
                for detail in cycle.medication_details.select_related('medication').all():
                    detail_data = {
                        'id': detail.id,
                        'medication': {
                            'id': detail.medication.id,
                            'item_name': detail.medication.item_name,
                            'item_seq': detail.medication.item_seq
                        },
                        'dosage': detail.dosage,
                        'dosage_unit': detail.dosage_unit,
                        'times_per_day': detail.times_per_day,
                        'days': detail.days,
                        'remaining_quantity': detail.remaining_quantity,
                        'is_active': detail.is_active
                    }
                    cycle_data['medication_details'].append(detail_data)
                
                data['cycles'].append(cycle_data)

        return data

    def list(self, request):
        groups = self.get_queryset()
        data = [self.get_medication_group_data(group) for group in groups]
        return Response(data)

    def retrieve(self, request, pk=None):
        group = self.get_object()
        data = self.get_medication_group_data(group, include_details=True)
        return Response(data)

    def create(self, request):
        try:
            # 필수 필드 검증
            required_fields = ['medical_info_id', 'group_name']
            for field in required_fields:
                if field not in request.data:
                    return Response({
                        'success': False,
                        'message': f'{field}는 필수 입력 항목입니다.'
                    }, status=400)

            # 의료 정보 조회
            medical_info = UserMedicalInfo.objects.get(
                id=request.data['medical_info_id'],
                user=request.user
            )

            # 복약 그룹 생성
            group = MedicationGroup.objects.create(
                medical_info=medical_info,
                group_name=request.data['group_name'],
                prescription_id=request.data.get('prescription_id')
            )

            data = self.get_medication_group_data(group)
            return Response({
                'success': True,
                'data': data,
                'message': '복약 그룹이 성공적으로 생성되었습니다.'
            }, status=201)

        except UserMedicalInfo.DoesNotExist:
            return Response({
                'success': False,
                'message': '해당하는 의료 정보를 찾을 수 없습니다.'
            }, status=404)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'복약 그룹 생성 중 오류가 발생했습니다: {str(e)}'
            }, status=400)

    @action(detail=False, methods=['get'])
    def active_groups(self, request):
        """활성 복약그룹 목록"""
        active_groups = self.get_queryset().filter(
            prescription__is_active=True
        )
        data = [self.get_medication_group_data(group, include_details=True) for group in active_groups]
        return Response({
            'success': True,
            'data': data,
            'message': '활성 복약 그룹 조회 성공'
        })


class MedicationGroupManager:
    """복약 그룹 관리를 위한 헬퍼 클래스"""

    @staticmethod
    def create_groups_for_shared_prescription(prescription):
        """공유 처방전에 대한 복약 그룹 자동 생성"""
        medical_infos = UserMedicalInfo.objects.filter(prescription=prescription)

        created_groups = []
        for medical_info in medical_infos:
            # 질병별로 별도 복약 그룹 생성
            group = MedicationGroup.objects.create(
                medical_info=medical_info,
                prescription=prescription,
                group_name=f"{medical_info.illness.name}_복약그룹"
            )

            # 해당 질병 관련 의약품들만 포함
            condition_medications = prescription.prescribed_medications.filter(
                # 질병별 의약품 필터링 로직
                medication__class_name__icontains=medical_info.illness.name
            )

            for presc_med in condition_medications:
                MedicationDetail.objects.create(
                    medication=presc_med.medication,
                    dosage_pattern=presc_med.dosage_pattern,
                    remaining_quantity=presc_med.total_quantity
                )

            created_groups.append(group)

        return created_groups