from django.urls import path, include
from rest_framework.routers import DefaultRouter


from .views import (
    PrescriptionViewSet, MedicationGroupViewSet,
    MedicationDetailViewSet, MedicationRecordViewSet, MedicationAlertViewSet
)
from .views.check_dosage_view import get_today_medications, get_next_dosage_time, get_medication_records, \
    create_medication_record, bulk_create_medication_records
from .views.prescription_renewal import PrescriptionRenewalAPI

app_name = 'bokyak'

router = DefaultRouter()
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'groups', MedicationGroupViewSet, basename='medication-group')
router.register(r'details', MedicationDetailViewSet, basename='medication-detail')
router.register(r'records', MedicationRecordViewSet, basename='medication-record')
router.register(r'alerts', MedicationAlertViewSet, basename='medication-alert')

urlpatterns = [
    path('', include(router.urls)),

    path('prescriptions/renew/', PrescriptionRenewalAPI.as_view(), name='prescription-renew'),
    # 복약 관련 API
    path('medications/today/', get_today_medications, name='get_today_medications'),
    path('medications/next-dosage/', get_next_dosage_time, name='get_next_dosage_time'),
    path('medications/records/', get_medication_records, name='get_medication_records'),
    path('medications/records/create/', create_medication_record, name='create_medication_record'),
    path('medications/records/bulk/', bulk_create_medication_records, name='bulk_create_medication_records'),
    #
    # # 복약 그룹 관리
    # path('medication-groups/', views.get_medication_groups, name='get_medication_groups'),
    # path('medication-groups/<str:group_id>/', views.get_medication_group_detail, name='get_medication_group_detail'),
    #
    # # 사용자 의료 정보
    # path('user-medical-info/', views.get_user_medical_info, name='get_user_medical_info'),
    #
    # # 통계 및 분석
    # path('analytics/adherence/', views.get_adherence_analytics, name='get_adherence_analytics'),
    # path('analytics/trends/', views.get_medication_trends, name='get_medication_trends'),
]