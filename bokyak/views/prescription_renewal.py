# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
import json

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
                    return Response({
                        'success': False,
                        'message': f'{field}는 필수 입력 항목입니다.'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 날짜 파싱
            prescription_date = parse_date(data['prescription_date'])
            if not prescription_date:
                return Response({
                    'success': False,
                    'message': '처방일자 형식이 올바르지 않습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 약물 데이터 검증
            medications_data = data['medications']
            if not isinstance(medications_data, list) or len(medications_data) == 0:
                return Response({
                    'success': False,
                    'message': '약물 데이터는 비어있지 않은 리스트여야 합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

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
                'data': result,
                'message': '처방전이 성공적으로 갱신되었습니다.'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'처방전 갱신 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
