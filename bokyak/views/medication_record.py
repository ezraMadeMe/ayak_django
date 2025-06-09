# bokyak/views/medication_record.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, date

from bokyak.models.medication_record import MedicationRecord
from bokyak.services.check_dosage_service import CheckDosageService
from bokyak.services.analytics_service import AnalyticsService
from bokyak.formatters import (
    format_medication_record,
    format_api_response
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_today_medications(request):
    """
    오늘의 복약 데이터 조회 API

    Query Parameters:
    - date: YYYY-MM-DD (선택사항, 기본값: 오늘)
    - group_id: 특정 그룹만 조회 (선택사항)
    """
    try:
        user_id = request.user.user_id

        # 날짜 파라미터 처리
        target_date_str = request.GET.get('date')
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        else:
            target_date = timezone.now().date()

        # 비즈니스 로직 호출
        medication_data = CheckDosageService.get_today_medication_groups(user_id, target_date)

        # 특정 그룹 필터링
        group_id = request.GET.get('group_id')
        if group_id:
            medication_data['medication_groups'] = [
                group for group in medication_data['medication_groups']
                if group['group_id'] == group_id
            ]

        return Response(format_api_response(
            success=True,
            data=medication_data,
            message=f'{target_date} 복약 데이터 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'데이터 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_next_dosage_time(request):
    """다음 복약 시간 조회 API (홈화면에서 현재 시간 기준 다음 복약 시간대 표시용)"""
    try:
        user_id = request.user.user_id
        next_dosage_data = CheckDosageService.get_next_dosage_time(user_id)

        return Response(format_api_response(
            success=True,
            data=next_dosage_data,
            message='다음 복약 시간 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'다음 복약 시간 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_medication_record(request):
    """
    복약 기록 생성 API

    Request Body:
    {
        "medication_detail_id": 123,
        "record_type": "TAKEN",  // TAKEN, MISSED, SKIPPED, SIDE_EFFECT
        "quantity_taken": 1.0,
        "notes": "식후 복용",
        "symptoms": ""  // 부작용 시에만
    }
    """
    try:
        user_id = request.user.user_id
        data = request.data

        # 필수 필드 검증
        required_fields = ['medication_detail_id', 'record_type']
        for field in required_fields:
            if field not in data:
                return Response(format_api_response(
                    success=False,
                    message=f'필수 필드가 누락되었습니다: {field}'
                ), status=status.HTTP_400_BAD_REQUEST)

        # 복약 기록 생성
        record = CheckDosageService.create_medication_record(
            user_id=user_id,
            medication_detail_id=data['medication_detail_id'],
            record_type=data['record_type'],
            quantity_taken=data.get('quantity_taken', 0.0),
            notes=data.get('notes', '')
        )

        return Response(format_api_response(
            success=True,
            data=format_medication_record(record),
            message='복약 기록이 성공적으로 저장되었습니다.'
        ), status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'복약 기록 저장 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_create_medication_records(request):
    """
    복수 복약 기록 생성 API (PillGrid에서 여러 약물 선택 시)

    Request Body:
    {
        "records": [
            {
                "medication_detail_id": 123,
                "record_type": "TAKEN",
                "quantity_taken": 1.0,
                "notes": "아침 복용"
            }
        ]
    }
    """
    try:
        user_id = request.user.user_id
        data = request.data

        if not data.get('records'):
            return Response(format_api_response(
                success=False,
                message='복약 기록 데이터가 없습니다.'
            ), status=status.HTTP_400_BAD_REQUEST)

        result = CheckDosageService.create_bulk_medication_records(user_id, data['records'])
        formatted_records = [format_medication_record(record) for record in result['created_records']]

        return Response(format_api_response(
            success=True,
            data=formatted_records,
            message=f'{len(formatted_records)}개의 복약 기록이 성공적으로 저장되었습니다.'
        ), status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'복약 기록 저장 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_records(request):
    """
    복약 기록 조회 API

    Query Parameters:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - medication_detail_id: 특정 약물 상세 ID (선택사항)
    """
    try:
        user_id = request.user.user_id

        # 날짜 범위 필수 체크
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        if not start_date_str or not end_date_str:
            return Response(format_api_response(
                success=False,
                message='시작일과 종료일은 필수입니다.'
            ), status=status.HTTP_400_BAD_REQUEST)

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 복약 기록 조회
        records = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_date__range=(start_date, end_date)
        )

        # 특정 약물 필터링
        medication_detail_id = request.GET.get('medication_detail_id')
        if medication_detail_id:
            records = records.filter(medication_detail_id=medication_detail_id)

        records = records.select_related(
            'medication_detail',
            'medication_detail__medication'
        ).order_by('-record_date', '-created_at')

        formatted_records = [format_medication_record(record) for record in records]

        return Response(format_api_response(
            success=True,
            data=formatted_records,
            message='복약 기록 조회 성공'
        ))

    except Exception as e:
        return Response(format_api_response(
            success=False,
            message=f'복약 기록 조회 실패: {str(e)}'
        ), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MedicationRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user=self.request.user
        ).select_related('medication_detail', 'medication_detail__medication')

    def list(self, request):
        records = self.get_queryset()
        data = [format_medication_record(record) for record in records]
        return Response(format_api_response(
            success=True,
            data=data,
            message='복약 기록 목록 조회 성공'
        ))

    def retrieve(self, request, pk=None):
        record = self.get_object()
        data = format_medication_record(record)
        return Response(format_api_response(
            success=True,
            data=data,
            message='복약 기록 상세 조회 성공'
        ))

    @action(detail=False, methods=['get'])
    def today_records(self, request):
        """오늘의 복약 기록"""
        today = timezone.now().date()
        records = self.get_queryset().filter(record_date=today)
        data = [format_medication_record(record) for record in records]
        return Response(format_api_response(
            success=True,
            data=data,
            message='오늘의 복약 기록 조회 성공'
        ))

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """복약 통계"""
        days = int(request.query_params.get('days', 30))
        stats = AnalyticsService.get_medication_statistics(
            user_id=request.user.user_id,
            days=days
        )
        return Response(format_api_response(
            success=True,
            data=stats,
            message='복약 통계 조회 성공'
        ))

    @action(detail=False, methods=['get'])
    def compliance(self, request):
        """복약 순응도"""
        days = int(request.query_params.get('days', 7))
        compliance_data = AnalyticsService.get_medication_compliance(
            user_id=request.user.user_id,
            days=days
        )
        return Response(format_api_response(
            success=True,
            data=compliance_data,
            message='복약 순응도 조회 성공'
        ))

    @action(detail=False, methods=['get'])
    def side_effects(self, request):
        """부작용 분석"""
        days = int(request.query_params.get('days', 30))
        side_effects_data = AnalyticsService.get_side_effects_analysis(
            user_id=request.user.user_id,
            days=days
        )
        return Response(format_api_response(
            success=True,
            data=side_effects_data,
            message='부작용 분석 조회 성공'
        ))

    @action(detail=False, methods=['get'])
    def timing_analysis(self, request):
        """복약 시간 준수 분석"""
        days = int(request.query_params.get('days', 30))
        timing_data = AnalyticsService.get_medication_timing_analysis(
            user_id=request.user.user_id,
            days=days
        )
        return Response(format_api_response(
            success=True,
            data=timing_data,
            message='복약 시간 준수 분석 조회 성공'
        ))