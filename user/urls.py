from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .views import (
    UserViewSet, HospitalViewSet, IllnessViewSet,
    MedicationViewSet, MainIngredientViewSet, UserMedicalInfoViewSet
)
app_name = 'user'

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'hospitals', HospitalViewSet, basename='hospital')
router.register(r'illnesses', IllnessViewSet, basename='illness')
router.register(r'medications', MedicationViewSet)
router.register(r'ingredients', MainIngredientViewSet)
router.register(r'medical-info', UserMedicalInfoViewSet, basename='medical-info')

urlpatterns = [
    path('', include(router.urls)),
]
# urlpatterns = [
#     # 카카오 로그인
#     path('kakao_login/',views.kakao_login, name='kakao_login'),
#     # 카카오 로그아웃
#     path('kakao_logout/', views.kakao_logout, name='kakao_logout'),
#     # 계정 삭제
#     path('delete_account/', views.delete_account, name='delete_account'),
#     # 사용자 등록 병원 정보
#     path('hospital_info/', views.hospital_info, name='hospital_info'),
#     # 질병/증상 정보
#     path('illness_info/', views.illness_info, name='illness_info'),
# ]