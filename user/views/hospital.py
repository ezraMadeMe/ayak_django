# user/views/hospital.py
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from user.models.ayakuser import AyakUser
from user.models.hospital import Hospital
from user.models.user_medical_info import UserMedicalInfo
from user.services.hospital_service import HospitalService


class HospitalViewSet(viewsets.ModelViewSet):
    """
    병원 관리를 위한 ViewSet
    - 사용자의 등록 병원 조회
    - 병원 상세 정보 조회
    - 외부 병원 정보 저장
    - 의료 정보 조회
    """
    queryset = Hospital.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'hospital_id'

    def get_queryset(self):
        return Hospital.objects.select_related('user').all()

    @action(detail=False, methods=['get'])
    def my_hospitals(self, request):
        """사용자가 등록한 모든 병원 조회"""
        try:
            hospitals = Hospital.objects.filter(
                user=request.user
            ).select_related('user').order_by('-created_at')

            data = [{
                'hospital_id': hospital.hospital_id,
                'hosp_name': hospital.hosp_name,
                'doctor_name': hospital.doctor_name,
                'address': hospital.address,
                'created_at': hospital.created_at.isoformat()
            } for hospital in hospitals]

            return Response({
                'success': True,
                'data': data,
                'count': len(data)
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'병원 목록 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def hospital_detail(self, request, hospital_id=None):
        """선택한 병원의 상세 정보 조회"""
        try:
            hospital = self.get_object()
            
            data = {
                'hospital_id': hospital.hospital_id,
                'hosp_name': hospital.hosp_name,
                'doctor_name': hospital.doctor_name
            }

            return Response({
                'success': True,
                'data': data
            })

        except Hospital.DoesNotExist:
            return Response({
                'success': False,
                'message': '해당 병원을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'병원 상세 정보 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def save_external_hospital(self, request):
        """외부 병원 정보를 저장"""
        try:
            # 필수 필드 검증
            required_fields = ['hosp_name', 'address']
            for field in required_fields:
                if not request.data.get(field):
                    return Response({
                        'success': False,
                        'message': f'{field}는 필수 입력 항목입니다.'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # 병원 생성 또는 업데이트
            with transaction.atomic():
                hospital, created = Hospital.objects.update_or_create(
                    user=request.user,
                    hosp_name=request.data['hosp_name'],
                    address=request.data['address'],
                    defaults={
                        'doctor_name': request.data.get('doctor_name'),
                        'phone_number': request.data.get('phone_number'),
                        'memo': request.data.get('memo')
                    }
                )

            message = '병원이 성공적으로 등록되었습니다.' if created else '병원 정보가 업데이트되었습니다.'
            return Response({
                'success': True,
                'data': {
                    'hospital_id': hospital.hospital_id,
                    'hosp_name': hospital.hosp_name,
                    'doctor_name': hospital.doctor_name
                },
                'message': message
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'병원 정보 저장 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def medical_info(self, request, hospital_id=None):
        """해당 병원의 의료 정보 조회"""
        try:
            hospital = self.get_object()
            
            medical_infos = UserMedicalInfo.objects.filter(
                user=request.user,
                hospital=hospital
            ).select_related('illness')

            data = [{
                'id': info.id,
                'illness_name': info.illness.ill_name if info.illness else None,
                'start_date': info.start_date.isoformat() if info.start_date else None,
                'end_date': info.end_date.isoformat() if info.end_date else None,
                'notes': info.notes
            } for info in medical_infos]

            return Response({
                'success': True,
                'data': data,
                'count': len(data)
            })

        except Hospital.DoesNotExist:
            return Response({
                'success': False,
                'message': '해당 병원을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'의료 정보 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

