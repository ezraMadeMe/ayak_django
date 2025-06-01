
# bokyak/tasks.py (Celery 태스크)
from celery import shared_task
from django.utils import timezone
from user.models.ayakuser import AyakUser
from .services.reminder_service import MedicationReminderService


@shared_task
def send_medication_reminders():
    """복약 알림 전송 (매시간 실행)"""
    current_time = timezone.now().time().replace(second=0, microsecond=0)

    # 현재 시간에 알림이 설정된 모든 사용자 조회
    users_with_alerts = AyakUser.objects.filter(
        medical_info__medication_groups__cycles__medication_details__alerts__alert_time=current_time,
        medical_info__medication_groups__cycles__medication_details__alerts__is_active=True,
        push_agree=True,
        is_active=True
    ).distinct()

    for user in users_with_alerts:
        alerts = MedicationReminderService.get_pending_medications(user, current_time)

        if alerts.exists():
            # 푸시 알림 전송 로직
            send_push_notification.delay(user.user_id, alerts.count())


@shared_task
def send_push_notification(user_id, medication_count):
    """푸시 알림 전송"""
    # FCM이나 다른 푸시 서비스 연동
    message = f"복용할 약물 {medication_count}개가 있습니다."
    # 실제 푸시 알림 전송 로직 구현
    pass


@shared_task
def check_refill_requirements():
    """매일 처방전 갱신 필요 여부 체크"""
    users = AyakUser.objects.filter(is_active=True, push_agree=True)

    for user in users:
        low_stock_medications = MedicationReminderService.get_refill_notifications(user)

        if low_stock_medications.exists():
            # 처방전 갱신 알림 전송
            send_refill_notification.delay(user.user_id, low_stock_medications.count())


@shared_task
def send_refill_notification(user_id, medication_count):
    """처방전 갱신 알림 전송"""
    message = f"잔여량이 부족한 약물 {medication_count}개가 있습니다. 처방전 갱신이 필요합니다."
    # 실제 알림 전송 로직 구현
    pass