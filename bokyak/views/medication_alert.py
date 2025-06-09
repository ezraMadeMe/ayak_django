# bokyak/views/medication_alert.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from bokyak.models.medication_alert import MedicationAlert


class MedicationAlertViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MedicationAlert.objects.filter(
            medication_detail__cycle__group__medical_info__user=self.request.user
        ).select_related(
            'medication_detail__medication',
            'medication_detail__cycle__group',
            'medication_detail__cycle__group__medical_info'
        )

    def get_medication_alert_data(self, alert):
        return {
            'id': alert.id,
            'medication_detail': {
                'id': alert.medication_detail.id,
                'medication': {
                    'id': alert.medication_detail.medication.id,
                    'item_name': alert.medication_detail.medication.item_name,
                    'item_seq': alert.medication_detail.medication.item_seq
                },
                'cycle': {
                    'id': alert.medication_detail.cycle.id,
                    'group': {
                        'id': alert.medication_detail.cycle.group.id,
                        'group_name': alert.medication_detail.cycle.group.group_name,
                        'medical_info': {
                            'id': alert.medication_detail.cycle.group.medical_info.id,
                            'user_id': alert.medication_detail.cycle.group.medical_info.user.user_id
                        }
                    }
                }
            },
            'alert_time': alert.alert_time.strftime('%H:%M') if alert.alert_time else None,
            'alert_type': alert.alert_type,
            'message': alert.message,
            'is_active': alert.is_active,
            'created_at': alert.created_at.isoformat() if alert.created_at else None,
            'updated_at': alert.updated_at.isoformat() if alert.updated_at else None
        }

    def list(self, request):
        alerts = self.get_queryset()
        data = [self.get_medication_alert_data(alert) for alert in alerts]
        return Response({
            'success': True,
            'data': data,
            'message': '알림 목록 조회 성공'
        })

    def retrieve(self, request, pk=None):
        alert = self.get_object()
        data = self.get_medication_alert_data(alert)
        return Response({
            'success': True,
            'data': data,
            'message': '알림 상세 조회 성공'
        })

    def create(self, request):
        try:
            # 필수 필드 검증
            required_fields = ['medication_detail_id', 'alert_time', 'alert_type']
            for field in required_fields:
                if field not in request.data:
                    return Response({
                        'success': False,
                        'message': f'{field}는 필수 입력 항목입니다.'
                    }, status=400)

            # 알림 생성
            alert = MedicationAlert.objects.create(
                medication_detail_id=request.data['medication_detail_id'],
                alert_time=request.data['alert_time'],
                alert_type=request.data['alert_type'],
                message=request.data.get('message', '')
            )

            data = self.get_medication_alert_data(alert)
            return Response({
                'success': True,
                'data': data,
                'message': '알림이 성공적으로 생성되었습니다.'
            }, status=201)

        except Exception as e:
            return Response({
                'success': False,
                'message': f'알림 생성 중 오류가 발생했습니다: {str(e)}'
            }, status=400)

    @action(detail=False, methods=['get'])
    def active_alerts(self, request):
        """활성 알림 목록"""
        active_alerts = self.get_queryset().filter(is_active=True)
        data = [self.get_medication_alert_data(alert) for alert in active_alerts]
        return Response({
            'success': True,
            'data': data,
            'message': '활성 알림 목록 조회 성공'
        })

    @action(detail=False, methods=['get'])
    def upcoming_alerts(self, request):
        """다가오는 알림들 (1시간 내)"""
        now = timezone.now().time()
        one_hour_later = (timezone.now() + timedelta(hours=1)).time()

        upcoming = self.get_queryset().filter(
            is_active=True,
            alert_time__gte=now,
            alert_time__lte=one_hour_later
        )

        data = [self.get_medication_alert_data(alert) for alert in upcoming]
        return Response({
            'success': True,
            'data': data,
            'message': '다가오는 알림 목록 조회 성공'
        })