
# user/serializers/hospital.py
from rest_framework import serializers
from user.models.hospital import Hospital

class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            'hospital_id', 'user', 'hosp_code', 'hosp_name',
            'hosp_type', 'doctor_name', 'address', 'phone_number'
        ]
        read_only_fields = ['hospital_id']
