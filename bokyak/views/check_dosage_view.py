# views.py
from django.db.models import Prefetch
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, date, timedelta
import json

from bokyak.models import MedicationRecord, MedicationGroup, MedicationCycle, MedicationDetail
from bokyak.serializers import MedicationRecordSerializer
from bokyak.serializers.check_dosage_serializer import TodayMedicationDataSerializer, NextDosageDataSerializer, \
    BulkRecordResponseSerializer
from bokyak.serializers.home_screen_serializer import HomeDataSerializer
from bokyak.services.check_dosage_service import CheckDosageService
from user.models import UserMedicalInfo

# views.py (완성된 API 뷰들)
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, date
from django.core.exceptions import ValidationError
from django.db import transaction
import json


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
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'success': False,
                    'message': '날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용해주세요.'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = timezone.now().date()

        # 특정 그룹 필터링
        group_id = request.GET.get('group_id')

        # 비즈니스 로직 호출
        medication_data = CheckDosageService.get_today_medication_groups(user_id, target_date)

        # 특정 그룹만 필터링
        if group_id:
            medication_data['medication_groups'] = [
                group for group in medication_data['medication_groups']
                if group['group_id'] == group_id
            ]

        # 시리얼라이저를 통한 응답
        serializer = TodayMedicationDataSerializer(medication_data)

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
    다음 복약 시간 조회 API
    현재 시간 기준 다음 복약 시간대 정보 반환
    """
    try:
        user_id = request.user.user_id

        # 비즈니스 로직 호출
        next_dosage_data = CheckDosageService.get_next_dosage_time(user_id)

        # 시리얼라이저를 통한 응답
        serializer = NextDosageDataSerializer(next_dosage_data)

        return Response({
            'success': True,
            'data': serializer.data,
            'message': '다음 복약 시간 조회 성공'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'다음 복약 시간 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_records(request):
    """
    복약 기록 조회 API

    Query Parameters:
    - start_date: YYYY-MM-DD (기본값: 7일 전)
    - end_date: YYYY-MM-DD (기본값: 오늘)
    - group_id: 특정 그룹만 조회
    - record_type: 특정 기록 타입만 조회 (TAKEN, MISSED, etc.)
    - medication_detail_id: 특정 약물만 조회
    """
    try:
        user_id = request.user.user_id

        # 날짜 범위 파라미터 처리
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        group_id = request.GET.get('group_id')
        record_type = request.GET.get('record_type')
        medication_detail_id = request.GET.get('medication_detail_id')

        # 기본값: 최근 7일
        if not start_date_str:
            start_date = timezone.now().date() - timezone.timedelta(days=7)
        else:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'success': False,
                    'message': 'start_date 형식이 올바르지 않습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

        if not end_date_str:
            end_date = timezone.now().date()
        else:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'success': False,
                    'message': 'end_date 형식이 올바르지 않습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

        # 사용자 권한 확인을 위한 기본 필터
        base_query = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_date__date__gte=start_date,
            record_date__date__lte=end_date
        ).select_related(
            'medication_detail__prescription_medication__medication',
            'medication_detail__cycle__group'
        ).order_by('-record_date')

        # 추가 필터링
        if record_type:
            base_query = base_query.filter(record_type=record_type)

        if medication_detail_id:
            base_query = base_query.filter(medication_detail_id=medication_detail_id)

        if group_id:
            base_query = base_query.filter(
                medication_detail__cycle__group__group_id=group_id
            )

        records = list(base_query)

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
                'total_count': len(records),
                'filters': {
                    'group_id': group_id,
                    'record_type': record_type,
                    'medication_detail_id': medication_detail_id
                }
            },
            'message': f'{len(records)}개의 복약 기록을 조회했습니다.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복약 기록 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_medication_record(request):
    """
    단일 복약 기록 생성 API

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

        # record_type 검증
        valid_record_types = ['TAKEN', 'MISSED', 'SKIPPED', 'SIDE_EFFECT']
        if data['record_type'] not in valid_record_types:
            return Response({
                'success': False,
                'message': f'유효하지 않은 record_type입니다. 가능한 값: {valid_record_types}'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 복약 기록 생성
        with transaction.atomic():
            record = CheckDosageService.create_medication_record(
                user_id=user_id,
                medication_detail_id=data['medication_detail_id'],
                record_type=data['record_type'],
                quantity_taken=float(data.get('quantity_taken', 0.0)),
                notes=data.get('notes', '')
            )

        # 응답 데이터 직렬화
        serializer = MedicationRecordSerializer(record)

        return Response({
            'success': True,
            'data': serializer.data,
            'message': '복약 기록이 성공적으로 저장되었습니다.'
        }, status=status.HTTP_201_CREATED)

    except PermissionError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_403_FORBIDDEN)

    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

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

        if not isinstance(records_data, list):
            return Response({
                'success': False,
                'message': 'records는 리스트 형태여야 합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 각 레코드의 필수 필드 검증
        for i, record_data in enumerate(records_data):
            required_fields = ['medication_detail_id', 'record_type']
            for field in required_fields:
                if field not in record_data:
                    return Response({
                        'success': False,
                        'message': f'records[{i}]에서 필수 필드가 누락되었습니다: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)

            # record_type 검증
            valid_record_types = ['TAKEN', 'MISSED', 'SKIPPED', 'SIDE_EFFECT']
            if record_data['record_type'] not in valid_record_types:
                return Response({
                    'success': False,
                    'message': f'records[{i}]에서 유효하지 않은 record_type입니다. 가능한 값: {valid_record_types}'
                }, status=status.HTTP_400_BAD_REQUEST)

        # 복수 복약 기록 생성
        with transaction.atomic():
            result = CheckDosageService.create_bulk_medication_records(
                user_id=user_id,
                records_data=records_data
            )

        # 응답 데이터 직렬화
        serializer = BulkRecordResponseSerializer(result)

        success_message = f'{result["total_created"]}개 복약 기록이 성공적으로 저장되었습니다.'
        if result["total_failed"] > 0:
            success_message += f' ({result["total_failed"]}개 실패)'

        return Response({
            'success': True,
            'data': serializer.data,
            'message': success_message
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복수 복약 기록 저장 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_groups(request):
    """
    사용자의 복약그룹 목록 조회 API

    Query Parameters:
    - is_active: true/false (활성 그룹만 조회)
    """
    try:
        user_id = request.user.user_id
        is_active = request.GET.get('is_active', 'true').lower() == 'true'

        # 사용자의 복약그룹 조회
        groups_query = MedicationGroup.objects.filter(
            medical_info__user__user_id=user_id
        ).select_related(
            'medical_info__hospital',
            'medical_info__illness',
            'prescription'
        )

        if is_active:
            groups_query = groups_query.filter(
                medicationcycle__is_active=True,
                medicationcycle__cycle_start__lte=timezone.now().date(),
                medicationcycle__cycle_end__gte=timezone.now().date()
            ).distinct()

        groups = list(groups_query)

        # 그룹 데이터 구성
        groups_data = []
        for group in groups:
            active_cycles = group.medicationcycle_set.filter(
                is_active=True,
                cycle_start__lte=timezone.now().date(),
                cycle_end__gte=timezone.now().date()
            )

            group_data = {
                'group_id': group.group_id,
                'group_name': group.group_name,
                'reminder_enabled': group.reminder_enabled,
                'hospital_name': group.medical_info.hospital.hosp_name,
                'prescription_date': group.prescription.prescription_date,
                'active_cycles_count': active_cycles.count(),
                'created_at': group.created_at,
            }
            groups_data.append(group_data)

        return Response({
            'success': True,
            'data': {
                'groups': groups_data,
                'total_count': len(groups_data)
            },
            'message': f'{len(groups_data)}개의 복약그룹을 조회했습니다.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복약그룹 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_group_detail(request, group_id):
    """
    특정 복약그룹의 상세 정보 조회 API
    """
    try:
        user_id = request.user.user_id

        # 권한 확인과 함께 그룹 조회
        try:
            group = MedicationGroup.objects.select_related(
                'medical_info__user',
                'medical_info__hospital',
                'medical_info__illness',
                'prescription'
            ).get(
                group_id=group_id,
                medical_info__user__user_id=user_id
            )
        except MedicationGroup.DoesNotExist:
            return Response({
                'success': False,
                'message': '복약그룹을 찾을 수 없거나 접근 권한이 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)

        # 활성 주기 조회
        active_cycles = group.medicationcycle_set.filter(
            is_active=True,
            cycle_start__lte=timezone.now().date(),
            cycle_end__gte=timezone.now().date()
        ).prefetch_related(
            'medicationdetail_set__prescription_medication__medication'
        )

        cycles_data = []
        for cycle in active_cycles:
            medication_details = cycle.medicationdetail_set.all()

            # 복약 상세 정보 구성
            details_data = []
            for detail in medication_details:
                detail_data = {
                    'medication_detail_id': detail.id,
                    'medication': {
                        'item_seq': detail.prescription_medication.medication.item_seq,
                        'item_name': detail.prescription_medication.medication.item_name,
                        'entp_name': detail.prescription_medication.medication.entp_name,
                        'class_name': detail.prescription_medication.medication.class_name,
                        'dosage_form': detail.prescription_medication.medication.dosage_form,
                    },
                    'actual_dosage_pattern': detail.actual_dosage_pattern,
                    'remaining_quantity': detail.remaining_quantity,
                    'patient_adjustments': detail.patient_adjustments,
                }
                details_data.append(detail_data)

            cycle_data = {
                'cycle_id': cycle.id,
                'cycle_number': cycle.cycle_number,
                'cycle_start': cycle.cycle_start,
                'cycle_end': cycle.cycle_end,
                'is_active': cycle.is_active,
                'medication_details': details_data,
            }
            cycles_data.append(cycle_data)

        # 그룹 상세 정보 구성
        group_detail = {
            'group_id': group.group_id,
            'group_name': group.group_name,
            'reminder_enabled': group.reminder_enabled,
            'medical_info': {
                'hospital_name': group.medical_info.hospital.hosp_name,
                'doctor_name': group.medical_info.hospital.doctor_name,
                'illness_name': group.medical_info.illness.ill_name,
            },
            'prescription': {
                'prescription_id': group.prescription.prescription_id,
                'prescription_date': group.prescription.prescription_date,
            },
            'active_cycles': cycles_data,
            'created_at': group.created_at,
            'updated_at': group.updated_at,
        }

        return Response({
            'success': True,
            'data': group_detail,
            'message': '복약그룹 상세 정보 조회 성공'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복약그룹 상세 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_medical_info(request):
    """
    사용자의 의료 정보 목록 조회 API
    """
    try:
        user_id = request.user.user_id

        medical_infos = UserMedicalInfo.objects.filter(
            user__user_id=user_id
        ).select_related(
            'hospital',
            'illness',
            'prescription'
        ).order_by('-created_at')

        medical_infos_data = []
        for info in medical_infos:
            info_data = {
                'id': info.id,
                'hospital': {
                    'hospital_id': info.hospital.hospital_id,
                    'hosp_name': info.hospital.hosp_name,
                    'hosp_type': info.hospital.hosp_type,
                    'doctor_name': info.hospital.doctor_name,
                    'address': info.hospital.address,
                    'phone_number': info.hospital.phone_number,
                },
                'illness': {
                    'illness_id': info.illness.illness_id,
                    'ill_name': info.illness.ill_name,
                    'ill_type': info.illness.ill_type,
                    'ill_code': info.illness.ill_code,
                    'is_chronic': info.illness.is_chronic,
                    'ill_start': info.illness.ill_start,
                    'ill_end': info.illness.ill_end,
                },
                'prescription': {
                    'prescription_id': info.prescription.prescription_id,
                    'prescription_date': info.prescription.prescription_date,
                    'is_active': info.prescription.is_active,
                },
                'is_primary': info.is_primary,
                'created_at': info.created_at,
            }
            medical_infos_data.append(info_data)

        return Response({
            'success': True,
            'data': {
                'medical_infos': medical_infos_data,
                'total_count': len(medical_infos_data)
            },
            'message': f'{len(medical_infos_data)}개의 의료 정보를 조회했습니다.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'의료 정보 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_adherence_analytics(request):
    """
    복약 순응도 분석 API

    Query Parameters:
    - period: week/month/quarter (기본값: month)
    - group_id: 특정 그룹만 분석
    """
    try:
        user_id = request.user.user_id
        period = request.GET.get('period', 'month')
        group_id = request.GET.get('group_id')

        # 기간 설정
        end_date = timezone.now().date()
        if period == 'week':
            start_date = end_date - timezone.timedelta(days=7)
        elif period == 'quarter':
            start_date = end_date - timezone.timedelta(days=90)
        else:  # month
            start_date = end_date - timezone.timedelta(days=30)

        # 기본 쿼리
        records_query = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_date__date__gte=start_date,
            record_date__date__lte=end_date
        )

        if group_id:
            records_query = records_query.filter(
                medication_detail__cycle__group__group_id=group_id
            )

        records = list(records_query.values(
            'record_type',
            'record_date__date',
            'medication_detail__prescription_medication__medication__item_name'
        ))

        # 분석 데이터 생성
        analytics_data = {
            'period': period,
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_records': len(records),
            'adherence_by_type': {},
            'daily_adherence': {},
            'medication_adherence': {},
        }

        # 타입별 분석
        for record in records:
            record_type = record['record_type']
            if record_type not in analytics_data['adherence_by_type']:
                analytics_data['adherence_by_type'][record_type] = 0
            analytics_data['adherence_by_type'][record_type] += 1

        # 일별 분석
        for record in records:
            date_str = record['record_date__date'].strftime('%Y-%m-%d')
            if date_str not in analytics_data['daily_adherence']:
                analytics_data['daily_adherence'][date_str] = {
                    'total': 0, 'taken': 0, 'missed': 0, 'skipped': 0
                }

            analytics_data['daily_adherence'][date_str]['total'] += 1
            if record['record_type'] == 'TAKEN':
                analytics_data['daily_adherence'][date_str]['taken'] += 1
            elif record['record_type'] == 'MISSED':
                analytics_data['daily_adherence'][date_str]['missed'] += 1
            elif record['record_type'] == 'SKIPPED':
                analytics_data['daily_adherence'][date_str]['skipped'] += 1

        # 약물별 분석
        for record in records:
            med_name = record['medication_detail__prescription_medication__medication__item_name']
            if med_name not in analytics_data['medication_adherence']:
                analytics_data['medication_adherence'][med_name] = {
                    'total': 0, 'taken': 0, 'adherence_rate': 0
                }

            analytics_data['medication_adherence'][med_name]['total'] += 1
            if record['record_type'] == 'TAKEN':
                analytics_data['medication_adherence'][med_name]['taken'] += 1

        # 순응도 비율 계산
        for med_name, data in analytics_data['medication_adherence'].items():
            if data['total'] > 0:
                data['adherence_rate'] = data['taken'] / data['total']

        return Response({
            'success': True,
            'data': analytics_data,
            'message': f'{period} 기간 복약 순응도 분석 완료'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복약 순응도 분석 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_medication_trends(request):
    """
    복약 트렌드 분석 API
    """
    try:
        user_id = request.user.user_id

        # 최근 30일 데이터
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=30)

        records = MedicationRecord.objects.filter(
            medication_detail__cycle__group__medical_info__user__user_id=user_id,
            record_date__date__gte=start_date,
            record_date__date__lte=end_date
        ).values(
            'record_date__date',
            'record_type'
        ).order_by('record_date__date')

        # 주간별 트렌드 분석
        weekly_trends = {}
        for record in records:
            week = record['record_date__date'].isocalendar()[1]  # 주차
            if week not in weekly_trends:
                weekly_trends[week] = {'total': 0, 'taken': 0, 'missed': 0}

            weekly_trends[week]['total'] += 1
            if record['record_type'] == 'TAKEN':
                weekly_trends[week]['taken'] += 1
            elif record['record_type'] == 'MISSED':
                weekly_trends[week]['missed'] += 1

        # 순응도 트렌드 계산
        for week_data in weekly_trends.values():
            week_data['adherence_rate'] = (
                week_data['taken'] / week_data['total']
                if week_data['total'] > 0 else 0
            )

        trends_data = {
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'weekly_trends': weekly_trends,
            'total_records': len(records),
        }

        return Response({
            'success': True,
            'data': trends_data,
            'message': '복약 트렌드 분석 완료'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            'success': False,
            'message': f'복약 트렌드 분석 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        medication_data = CheckDosageService.get_today_medication_groups(user_id, target_date)

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
        medication_data = CheckDosageService.get_today_medication_groups(user_id, current_date)

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
        record = CheckDosageService.create_medication_record(
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
                record = CheckDosageService.create_medication_record(
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
