from django.urls import path

from user import views

app_name = 'user'

urlpatterns = [
    # 카카오 로그인
    path('kakao_login/',views.kakao_login, name='kakao_login'),
    # 카카오 로그아웃
    path('kakao_logout/', views.kakao_logout, name='kakao_logout'),
    # 계정 삭제
    path('delete_account/', views.delete_account, name='delete_account'),

    # 사용자 등록 병원 정보
    path('hospital_info/', views.hospital_info, name='hospital_info'),
    # 질병/증상 정보
    path('illness_info/', views.illness_info, name='illness_info'),

]