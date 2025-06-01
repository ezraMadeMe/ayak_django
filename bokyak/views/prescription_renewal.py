
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
import json

from bokyak.models.medication_cycle import MedicationCycle
from bokyak.services.prescription_renewal_service import PrescriptionRenewalService


class PrescriptionRenewalAPI(APIView):
    """처방전 갱신 API"""

    def post(self, request):
        try:
            data = request.data

            # 필수 데이터 검증
            required_fields = ['user_id', 'hospital_id', 'illness_id',
                               'prescription_date', 'medications']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {'error': f'{field} is required'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 날짜 파싱
            prescription_date = parse_date(data['prescription_date'])
            if not prescription_date:
                return Response(
                    {'error': 'Invalid prescription_date format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 약물 데이터 검증
            medications_data = data['medications']
            if not isinstance(medications_data, list) or len(medications_data) == 0:
                return Response(
                    {'error': 'medications must be a non-empty list'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 처방전 갱신 처리
            result = PrescriptionRenewalService.renew_prescription(
                user_id=data['user_id'],
                hospital_id=data['hospital_id'],
                illness_id=data['illness_id'],
                old_prescription_id=data.get('old_prescription_id'),
                prescription_date=prescription_date,
                medications_data=medications_data
            )

            return Response({
                'success': True,
                'message': '처방전이 성공적으로 갱신되었습니다.',
                'data': result
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'처방전 갱신 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CycleExpirationCheckAPI(APIView):
    """주기 만료 확인 API"""

    def get(self, request, user_id):
        try:
            from datetime import date, timedelta

            today = date.today()
            warning_days = 7  # 7일 전부터 경고

            # 만료 예정 주기들 조회
            expiring_cycles = MedicationCycle.objects.filter(
                medication_groups__user_medical_info__user_id=user_id,
                is_active=True,
                cycle_end__lte=today + timedelta(days=warning_days),
                cycle_end__gte=today
            ).select_related(
                'medication_groups__user_medical_info__prescription',
                'medication_groups__user_medical_info__hospital',
                'medication_groups__user_medical_info__illness'
            )

            # 이미 만료된 주기들
            expired_cycles = MedicationCycle.objects.filter(
                medication_groups__user_medical_info__user_id=user_id,
                is_active=True,
                cycle_end__lt=today
            ).select_related(
                'medication_groups__user_medical_info__prescription',
                'medication_groups__user_medical_info__hospital',
                'medication_groups__user_medical_info__illness'
            )

            response_data = {
                'expiring_soon': [],
                'expired': [],
                'needs_renewal': len(expired_cycles) > 0
            }

            # 만료 예정 데이터 구성
            for cycle in expiring_cycles:
                days_remaining = (cycle.cycle_end - today).days
                response_data['expiring_soon'].append({
                    'cycle_id': cycle.id,
                    'group_id': cycle.group_id,
                    'group_name': cycle.medication_groups.group_name,
                    'cycle_end': cycle.cycle_end.isoformat(),
                    'days_remaining': days_remaining,
                    'hospital_name': cycle.medication_groups.user_medical_info.hospital.hosp_name,
                    'prescription_id': cycle.medication_groups.prescription_id
                })

            # 만료된 데이터 구성
            for cycle in expired_cycles:
                days_overdue = (today - cycle.cycle_end).days
                response_data['expired'].append({
                    'cycle_id': cycle.id,
                    'group_id': cycle.group_id,
                    'group_name': cycle.medication_groups.group_name,
                    'cycle_end': cycle.cycle_end.isoformat(),
                    'days_overdue': days_overdue,
                    'hospital_name': cycle.medication_groups.user_medical_info.hospital.hosp_name,
                    'prescription_id': cycle.medication_groups.prescription_id
                })

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'error': f'주기 만료 확인 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
