from rest_framework import serializers

from .models import Hospital, Illness, User


# 사용자 기본 정보
class UserSerializer(serializers.Serializer):
    class Meta:
        model = User
        fields = '__all__'

# 사용자 등록 정보 - 병원
class HospotalSerializer(serializers.Serializer):
    class Meta:
        model = Hospital
        fields = ['hosp_name', 'hosp_id', 'doctor_name']

# 사용자 등록 정보 - 질병/증상
class IllnessSerializer(serializers.Serializer):
    class Meta:
        model = Illness
        fields = ['ill_type', 'ill_id', 'ill_name', 'ill_start', 'ill_end']

# 사용자 종합 정보
class UserProfileSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    user_name = serializers.CharField()
    user_hosp = HospotalSerializer()
    user_ill = IllnessSerializer()


