# bokyak/views/medication_record.py
from rest_framework import viewsets
from rest_framework.decorators import action
from datetime import timedelta
from bokyak.models.medication_record import MedicationRecord, MedicationDetail
from bokyak.serializers import MedicationRecordSerializer, CreateMedicationRecordSerializer
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, date
import json

from bokyak.serializers.medication_record import HomeDataSerializer
from bokyak.services.check_medication_service import MedicationService


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

        # 특정 그룹 필터링
        group_id = request.GET.get('group_id')

        # 비즈니스 로직 호출
        medication_data = MedicationService.get_today_medication_groups(user_id, target_date)

        # 특정 그룹만 필터링
        if group_id:
            medication_data['medication_groups'] = [
                group for group in medication_data['medication_groups']
                if group['group_id'] == group_id
            ]

        # 시리얼라이저를 통한 응답
        serializer = HomeDataSerializer(medication_data)

        return Response({
            'success': True,
            'data': serializer.data,
            'message': f'{target_date} 복약 데이터 조회 성공'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'데이터 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_next_dosage_time(request):
    """
    다음 복약 시간 조회 API (홈화면에서 현재 시간 기준 다음 복약 시간대 표시용)
    """
    try:
        user_id = request.user.user_id
        current_time = timezone.now().time()
        current_date = timezone.now().date()

        # 시간대 우선순위 매핑
        time_ranges = {
            'morning': (6, 10),  # 6시-10시
            'lunch': (11, 14),  # 11시-14시
            'evening': (17, 20),  # 17시-20시
            'bedtime': (21, 23),  # 21시-23시
        }

        # 현재 시간 기준 다음 복약 시간 찾기
        current_hour = current_time.hour
        next_dosage_time = None

        for dosage_time, (start_hour, end_hour) in time_ranges.items():
            if current_hour < start_hour:
                next_dosage_time = dosage_time
                break

        # 오늘 남은 복약 시간이 없으면 내일 아침
        if not next_dosage_time:
            next_dosage_time = 'morning'
            current_date = current_date + timezone.timedelta(days=1)

        # 해당 시간대의 복약 데이터 조회
        medication_data = MedicationService.get_today_medication_groups(user_id, current_date)

        next_medications = []
        for group in medication_data['medication_groups']:
            if next_dosage_time in group['medications_by_time']:
                next_medications.extend(group['medications_by_time'][next_dosage_time])

        return Response({
            'success': True,
            'data': {
                'next_dosage_time': next_dosage_time,
                'target_date': current_date,
                'medications': next_medications,
                'total_count': len(next_medications)
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'다음 복약 시간 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                return Response({
                    'success': False,
                    'message': f'필수 필드가 누락되었습니다: {field}'
                }, status=status.HTTP_400_BAD_REQUEST)

        # 복약 기록 생성
        record = MedicationService.create_medication_record(
            user_id=user_id,
            medication_detail_id=data['medication_detail_id'],
            record_type=data['record_type'],
            quantity_taken=data.get('quantity_taken', 0.0),
            notes=data.get('notes', '')
        )

        # 응답 데이터 직렬화
        serializer = MedicationRecordSerializer(record)

        return Response({
            'success': True,
            'data': serializer.data,
            'message': '복약 기록이 성공적으로 저장되었습니다.'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복약 기록 저장 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            },
            {
                "medication_detail_id": 124,
                "record_type": "TAKEN",
                "quantity_taken": 1.0,
                "notes": "아침 복용"
            }
        ]
    }
    """
    try:
        user_id = request.user.user_id
        records_data = request.data.get('records', [])

        if not records_data:
            return Response({
                'success': False,
                'message': '복약 기록 데이터가 없습니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        created_records = []
        failed_records = []

        for record_data in records_data:
            try:
                record = MedicationService.create_medication_record(
                    user_id=user_id,
                    medication_detail_id=record_data['medication_detail_id'],
                    record_type=record_data['record_type'],
                    quantity_taken=record_data.get('quantity_taken', 0.0),
                    notes=record_data.get('notes', '')
                )
                created_records.append(MedicationRecordSerializer(record).data)

            except Exception as e:
                failed_records.append({
                    'medication_detail_id': record_data.get('medication_detail_id'),
                    'error': str(e)
                })

        return Response({
            'success': True,
            'data': {
                'created_records': created_records,
                'failed_records': failed_records,
                'total_requested': len(records_data),
                'total_created': len(created_records),
                'total_failed': len(failed_records)
            },
            'message': f'{len(created_records)}개 복약 기록이 성공적으로 저장되었습니다.'
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복수 복약 기록 저장 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_records(request):
    """
    복약 기록 조회 API

    Query Parameters:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - group_id: 특정 그룹만 조회
    - record_type: 특정 기록 타입만 조회 (TAKEN, MISSED, etc.)
    """
    try:
        user_id = request.user.user_id

        # 날짜 범위 파라미터
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        group_id = request.GET.get('group_id')
        record_type = request.GET.get('record_type')

        # 기본값: 최근 7일
        if not start_date_str:
            start_date = timezone.now().date() - timezone.timedelta(days=7)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()

        if not end_date_str:
            end_date = timezone.now().date()
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        # 복약 기록 조회 (실제 구현 시 더 복잡한 필터링 로직)
        records = MedicationRecord.objects.filter(
            record_date__date__gte=start_date,
            record_date__date__lte=end_date
        )

        if record_type:
            records = records.filter(record_type=record_type)

        # 시리얼라이저를 통한 응답
        serializer = MedicationRecordSerializer(records, many=True)

        return Response({
            'success': True,
            'data': {
                'records': serializer.data,
                'date_range': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'total_count': len(serializer.data)
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복약 기록 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MedicationRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user=self.request.user
        ).select_related('medication_detail__medication')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMedicationRecordSerializer
        return MedicationRecordSerializer

    @action(detail=False, methods=['get'])
    def today_records(self, request):
        """오늘의 복약 기록"""
        today = timezone.now().date()
        today_records = self.get_queryset().filter(
            record_date__date=today
        ).order_by('-record_date')

        serializer = self.get_serializer(today_records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """복약 통계"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now().date() - timedelta(days=days)

        records = self.get_queryset().filter(record_date__date__gte=start_date)

        total_records = records.count()
        taken_records = records.filter(record_type=MedicationRecord.RecordType.TAKEN).count()
        missed_records = records.filter(record_type=MedicationRecord.RecordType.MISSED).count()

        compliance_rate = (taken_records / total_records * 100) if total_records > 0 else 0

        data = {
            'period_days': days,
            'total_records': total_records,
            'taken_records': taken_records,
            'missed_records': missed_records,
            'compliance_rate': round(compliance_rate, 2)
        }
        return Response(data)

    @action(detail=False, methods=['post'])
    def bulk_record(self, request):
        """여러 약물 한번에 복용 기록"""
        medication_details = request.data.get('medication_details', [])
        record_type = request.data.get('record_type', MedicationRecord.RecordType.TAKEN)
        record_date = request.data.get('record_date', timezone.now())
        notes = request.data.get('notes', '')

        created_records = []
        for detail_data in medication_details:
            detail_id = detail_data.get('medication_detail_id')
            quantity = detail_data.get('quantity_taken', 1)

            try:
                medication_detail = MedicationDetail.objects.get(
                    id=detail_id,
                    cycle__group__medical_info__user=self.request.user
                )

                record = MedicationRecord.objects.create(
                    medication_detail=medication_detail,
                    record_type=record_type,
                    record_date=record_date,
                    quantity_taken=quantity,
                    notes=notes
                )

                # 복용 기록인 경우 잔여량 업데이트
                if record_type == MedicationRecord.RecordType.TAKEN:
                    medication_detail.remaining_quantity -= quantity
                    medication_detail.save()

                created_records.append(record)

            except MedicationDetail.DoesNotExist:
                continue

        serializer = MedicationRecordSerializer(created_records, many=True)
        return Response(serializer.data)