# bokyak/views/medication_group.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from bokyak.models.medication_cycle import MedicationCycle
from bokyak.models.medication_detail import MedicationDetail
from bokyak.models.medication_group import MedicationGroup
from bokyak.serializers import MedicationGroupSerializer, MedicationGroupDetailSerializer
from user.models import UserMedicalInfo


class MedicationGroupViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationGroup.objects.filter(
            medical_info__user=self.request.user
        ).select_related('medical_info__hospital', 'medical_info__illness', 'prescription')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MedicationGroupDetailSerializer
        return MedicationGroupSerializer

    @action(detail=False, methods=['get'])
    def active_groups(self, request):
        """활성 복약그룹 목록"""
        active_groups = self.get_queryset().filter(
            prescription__is_active=True
        )
        serializer = MedicationGroupDetailSerializer(active_groups, many=True)
        return Response(serializer.data)


class MedicationGroupManager:
    """복약 그룹 관리를 위한 헬퍼 클래스"""

    @staticmethod
    def create_groups_for_shared_prescription(prescription):
        """공유 처방전에 대한 복약 그룹 자동 생성"""
        medical_infos = UserMedicalInfo.objects.filter(prescription=prescription)

        for medical_info in medical_infos:
            # 질병별로 별도 복약 그룹 생성
            group = MedicationGroup.objects.create(
                medical_info=medical_info,
                prescription=prescription,
                group_name=f"{medical_info.illness.ill_name}_복약그룹"
            )

            # 첫 번째 주기 생성
            cycle = MedicationCycle.objects.create(
                group=group,
                cycle_start=prescription.prescription_date
            )

            # 해당 질병 관련 의약품들만 포함
            condition_medications = prescription.prescribed_medications.filter(
                # 질병별 의약품 필터링 로직
                medication__class_name__icontains=medical_info.illness.ill_name
            )

            for presc_med in condition_medications:
                MedicationDetail.objects.create(
                    cycle=cycle,
                    medication=presc_med.medication,
                    dosage_pattern=presc_med.dosage_pattern,
                    remaining_quantity=presc_med.total_quantity
                )