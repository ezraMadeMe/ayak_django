# user/views/illness.py
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from user.models.illness import Illness
from user.models.user_medical_info import UserMedicalInfo


class IllnessViewSet(viewsets.ModelViewSet):
    """
    질병/증상 관리를 위한 ViewSet
    - 사용자의 등록 질병/증상 조회
    - 질병/증상 정보 저장
    - 의료 정보 조회
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Illness.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def my_illnesses(self, request):
        """사용자가 등록한 모든 질병/증상 조회"""
        try:
            illnesses = self.get_queryset().order_by('-created_at')

            data = [{
                'id': illness.id,
                'ill_name': illness.ill_name,
                'is_chronic': illness.is_chronic,
                'diagnosis_date': illness.diagnosis_date.isoformat() if illness.diagnosis_date else None,
                'memo': illness.memo,
                'created_at': illness.created_at.isoformat()
            } for illness in illnesses]

            return Response({
                'success': True,
                'data': data,
                'count': len(data)
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'질병/증상 목록 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def save_illness(self, request):
        """질병/증상 정보를 저장 (캐시테이블 또는 수기 등록)"""
        try:
            # 필수 필드 검증
            if not request.data.get('ill_name'):
                return Response({
                    'success': False,
                    'message': '질병/증상명은 필수 입력 항목입니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 질병/증상 생성 또는 업데이트
            with transaction.atomic():
                illness, created = Illness.objects.update_or_create(
                    user=request.user,
                    ill_name=request.data['ill_name'],
                    defaults={
                        'is_chronic': request.data.get('is_chronic', False),
                        'diagnosis_date': request.data.get('diagnosis_date'),
                        'memo': request.data.get('memo')
                    }
                )

            message = '질병/증상이 성공적으로 등록되었습니다.' if created else '질병/증상 정보가 업데이트되었습니다.'
            return Response({
                'success': True,
                'data': {
                    'id': illness.id,
                    'ill_name': illness.ill_name,
                    'is_chronic': illness.is_chronic
                },
                'message': message
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'질병/증상 정보 저장 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def medical_info(self, request, pk=None):
        """해당 질병/증상의 의료 정보 조회"""
        try:
            illness = self.get_object()
            
            medical_infos = UserMedicalInfo.objects.filter(
                user=request.user,
                illness=illness
            ).select_related('hospital')

            data = [{
                'id': info.id,
                'hospital_name': info.hospital.hosp_name if info.hospital else None,
                'start_date': info.start_date.isoformat() if info.start_date else None,
                'end_date': info.end_date.isoformat() if info.end_date else None,
                'notes': info.notes
            } for info in medical_infos]

            return Response({
                'success': True,
                'data': data,
                'count': len(data)
            })

        except Illness.DoesNotExist:
            return Response({
                'success': False,
                'message': '해당 질병/증상을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'의료 정보 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)