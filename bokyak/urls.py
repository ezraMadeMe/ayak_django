from django.urls import path

from bokyak import views

app_name = 'bokyak'

urlpatterns = [
    # 복약 세부 정보
    path('bokyak_detail/', views.bokyak_detail, name='bokyak_detail'),
    # 복약 그룹
    path('bokyak_group/', views.bokyak_group, name='bokyak_group'),
    # 복약 주기
    path('bokyak_cycle/', views.bokyak_cycle, name='bokyak_cycle'),
    # 복약 기록 정보
    path('bokyak_record/', views.bokyak_record, name='bokyak_record'),
]