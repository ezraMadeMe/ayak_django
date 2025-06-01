# user/serializers/medical_info.py
from rest_framework import serializers
from user.models.user_medical_info import UserMedicalInfo


class UserMedicalInfoSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source='hospital.hosp_name', read_only=True)
    illness_name = serializers.CharField(source='illness.ill_name', read_only=True)
    doctor_name = serializers.CharField(source='hospital.doctor_name', read_only=True)

    class Meta:
        model = UserMedicalInfo
        fields = [
            'id', 'user', 'hospital', 'illness', 'is_primary',
            'hospital_name', 'illness_name', 'doctor_name'
        ]