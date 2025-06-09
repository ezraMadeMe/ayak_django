# user/views/medical_info.py
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from user.models.user_medical_info import UserMedicalInfo
from bokyak.models.prescription import Prescription


class UserMedicalInfoViewSet(viewsets.ModelViewSet):
    """
    사용자 의료 정보 관리를 위한 ViewSet
    - 사용자의 모든 의료 정보 조회
    - 병원/질병 기준 의료 정보 검색
    - 의료 정보 등록 및 처방전 생성
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserMedicalInfo.objects.filter(
            user=self.request.user
        ).select_related('hospital', 'illness')

    @action(detail=False, methods=['get'])
    def my_medical_info(self, request):
        """사용자의 모든 의료 정보 조회"""
        try:
            medical_infos = self.get_queryset().order_by('-created_at')
            
            data = [{
                'id': info.id,
                'hospital': {
                    'id': info.hospital.id,
                    'name': info.hospital.hosp_name,
                    'address': info.hospital.address
                } if info.hospital else None,
                'illness': {
                    'id': info.illness.id,
                    'name': info.illness.ill_name,
                    'is_chronic': info.illness.is_chronic
                } if info.illness else None,
                'prescription': {
                    'id': info.prescription.id,
                    'prescription_date': info.prescription.prescription_date.isoformat() if info.prescription and info.prescription.prescription_date else None
                } if info.prescription else None,
                'created_at': info.created_at.isoformat()
            } for info in medical_infos]

            return Response({
                'success': True,
                'data': data,
                'count': len(data)
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'의료 정보 목록 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """병원명 또는 질병명으로 의료 정보 검색"""
        try:
            queryset = self.get_queryset()
            
            hospital_name = request.query_params.get('hospital_name')
            illness_name = request.query_params.get('illness_name')

            if hospital_name:
                queryset = queryset.filter(hospital__hosp_name__icontains=hospital_name)
            if illness_name:
                queryset = queryset.filter(illness__ill_name__icontains=illness_name)

            data = [{
                'id': info.id,
                'hospital': {
                    'id': info.hospital.id,
                    'name': info.hospital.hosp_name
                } if info.hospital else None,
                'illness': {
                    'id': info.illness.id,
                    'name': info.illness.ill_name
                } if info.illness else None,
                'prescription': {
                    'id': info.prescription.id
                } if info.prescription else None,
                'created_at': info.created_at.isoformat()
            } for info in queryset.order_by('-created_at')]

            return Response({
                'success': True,
                'data': data,
                'count': len(data)
            })

        except Exception as e:
            return Response({
                'success': False,
                'message': f'의료 정보 검색 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def register_visit(self, request):
        """의료 정보 등록 및 빈 처방전 생성"""
        try:
            # 필수 필드 검증
            required_fields = ['hospital_id', 'illness_id']
            missing_fields = [field for field in required_fields if not request.data.get(field)]
            
            if missing_fields:
                return Response({
                    'success': False,
                    'message': f'다음 필드는 필수입니다: {", ".join(missing_fields)}'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # 의료 정보 생성
                medical_info = UserMedicalInfo.objects.create(
                    user=request.user,
                    hospital_id=request.data['hospital_id'],
                    illness_id=request.data['illness_id']
                )

                # 빈 처방전 생성
                prescription = Prescription.objects.create(
                    medical_info=medical_info
                )

                # 처방전 연결
                medical_info.prescription = prescription
                medical_info.save()

            return Response({
                'success': True,
                'data': {
                    'medical_info_id': medical_info.id,
                    'prescription_id': prescription.id,
                    'hospital_name': medical_info.hospital.hosp_name,
                    'illness_name': medical_info.illness.ill_name
                },
                'message': '진료 정보와 처방전이 성공적으로 생성되었습니다.'
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'진료 정보 등록 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)