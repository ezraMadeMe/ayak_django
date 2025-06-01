# user/views/hospital.py
from venv import logger

from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from user import models
from user.models import AyakUser
from user.models.hospital import Hospital
from user.serializers import HospitalSerializer


class HospitalViewSet(viewsets.ModelViewSet):
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    lookup_field = 'hospital_id'

    def get_queryset(self):
        """기본적으로 모든 병원 조회, 필터링은 액션에서 처리"""
        return Hospital.objects.select_related('user').all()

    def create(self, request, *args, **kwargs):
        """병원 등록"""
        logger.info(f"병원 등록 요청 데이터: {request.data}")

        try:
            # 사용자 ID 검증 및 가져오기
            user_id = request.data.get('user_id')
            if not user_id:
                return Response({
                    'success': False,
                    'message': '사용자 ID가 필요합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # 사용자 존재 확인
            try:
                user = AyakUser.objects.get(user_id=user_id)
            except AyakUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '존재하지 않는 사용자입니다.'
                }, status=status.HTTP_404_NOT_FOUND)

            # 요청 데이터에서 user 필드를 사용자 객체로 설정
            data = request.data.copy()
            data['user'] = user.user_id

            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                with transaction.atomic():
                    hospital = serializer.save()

                logger.info(f"병원 등록 성공: {hospital.hospital_id}")
                return Response({
                    'success': True,
                    'data': serializer.data,
                    'message': '병원이 성공적으로 등록되었습니다.'
                }, status=status.HTTP_201_CREATED)
            else:
                logger.warning(f"병원 등록 유효성 검사 실패: {serializer.errors}")
                return Response({
                    'success': False,
                    'message': '입력 데이터가 올바르지 않습니다.',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"병원 등록 중 오류: {e}")
            return Response({
                'success': False,
                'message': '병원 등록 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def get_user_hospitals(self, request, user_id=None):
        """특정 사용자의 병원 목록 조회"""
        try:
            # 사용자 존재 확인
            user = get_object_or_404(AyakUser, user_id=user_id)

            # 해당 사용자의 병원들 조회
            hospitals = Hospital.objects.filter(user=user).order_by('-created_at')
            serializer = self.get_serializer(hospitals, many=True)

            return Response({
                'success': True,
                'data': serializer.data,
                'count': hospitals.count()
            })

        except Exception as e:
            logger.error(f"사용자 병원 목록 조회 오류: {e}")
            return Response({
                'success': False,
                'message': '병원 목록 조회 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, *args, **kwargs):
        """병원 정보 수정"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # 사용자 권한 확인 (본인 병원만 수정 가능)
        user_id = request.data.get('user_id')
        if user_id and instance.user.user_id != user_id:
            return Response({
                'success': False,
                'message': '본인이 등록한 병원만 수정할 수 있습니다.'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            hospital = serializer.save()
            return Response({
                'success': True,
                'data': serializer.data,
                'message': '병원 정보가 성공적으로 수정되었습니다.'
            })
        else:
            return Response({
                'success': False,
                'message': '입력 데이터가 올바르지 않습니다.',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """병원 삭제"""
        instance = self.get_object()

        # 사용자 권한 확인 (본인 병원만 삭제 가능)
        user_id = request.query_params.get('user_id') or request.data.get('user_id')
        if user_id and instance.user.user_id != user_id:
            return Response({
                'success': False,
                'message': '본인이 등록한 병원만 삭제할 수 있습니다.'
            }, status=status.HTTP_403_FORBIDDEN)

        hospital_name = instance.hosp_name
        instance.delete()

        return Response({
            'success': True,
            'message': f'{hospital_name} 병원이 삭제되었습니다.'
        }, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """병원 검색 (등록된 병원 중에서)"""
        keyword = request.query_params.get('keyword', '').strip()
        user_id = request.query_params.get('user_id')

        if not keyword:
            return Response({
                'success': False,
                'message': '검색 키워드가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset()

        # 특정 사용자의 병원만 검색
        if user_id:
            queryset = queryset.filter(user__user_id=user_id)

        # 병원명, 주소, 담당의로 검색
        hospitals = queryset.filter(
            models.Q(hosp_name__icontains=keyword) |
            models.Q(address__icontains=keyword) |
            models.Q(doctor_name__icontains=keyword)
        ).order_by('hosp_name')

        serializer = self.get_serializer(hospitals, many=True)

        return Response({
            'success': True,
            'data': serializer.data,
            'count': hospitals.count()
        })