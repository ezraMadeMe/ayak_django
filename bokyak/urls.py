from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PrescriptionViewSet, MedicationGroupViewSet, MedicationCycleViewSet,
    MedicationDetailViewSet, MedicationRecordViewSet, MedicationAlertViewSet
)
from bokyak import views
from .views.prescription_renewal import PrescriptionRenewalAPI, CycleExpirationCheckAPI

app_name = 'bokyak'

router = DefaultRouter()
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'groups', MedicationGroupViewSet, basename='medication-group')
router.register(r'cycles', MedicationCycleViewSet, basename='medication-cycle')
router.register(r'details', MedicationDetailViewSet, basename='medication-detail')
router.register(r'records', MedicationRecordViewSet, basename='medication-record')
router.register(r'alerts', MedicationAlertViewSet, basename='medication-alert')

urlpatterns = [
    path('', include(router.urls)),
    path('prescriptions/renew/', PrescriptionRenewalAPI.as_view(), name='prescription-renew'),
    path('cycles/expiration-check/<str:user_id>/', CycleExpirationCheckAPI.as_view(), name='cycle-expiration-check'),
]

# urlpatterns = [
#     # 복약 세부 정보
#     path('bokyak_detail/', views.bokyak_detail, name='bokyak_detail'),
#     # 복약 그룹
#     path('bokyak_group/', views.bokyak_group, name='bokyak_group'),
#     # 복약 주기
#     path('bokyak_cycle/', views.bokyak_cycle, name='bokyak_cycle'),
#     # 복약 기록 정보
#     path('bokyak_record/', views.bokyak_record, name='bokyak_record'),
# ]