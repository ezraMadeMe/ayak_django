from django.db import transaction
from rest_framework import serializers

from bokyak.models.prescription import Prescription
from bokyak.models.prescription_medication import PrescriptionMedication
from bokyak.serializers.medication_info_serializer import MedicationGroupSerializer

from user.models import UserMedicalInfo


class PrescriptionMedicationSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication.item_name', read_only=True)
    medication_image = serializers.ImageField(source='medication.item_image', read_only=True)

    class Meta:
        model = PrescriptionMedication
        fields = [
            'medication', 'medication_name', 'medication_image',
            'dosage_pattern', 'duration_days', 'total_quantity'
        ]


class PrescriptionSerializer(serializers.ModelSerializer):
    prescribed_medications = PrescriptionMedicationSerializer(many=True, read_only=True)
    hospital_name = serializers.CharField(source='medical_info.hospital.hosp_name', read_only=True)
    illness_name = serializers.CharField(source='medical_info.illness.ill_name', read_only=True)
    user_name = serializers.CharField(source='medical_info.user.user_name', read_only=True)

    class Meta:
        model = Prescription
        fields = [
            'prescription_id', 'medical_info', 'prescription_date',
            'previous_prescription', 'is_active', 'prescribed_medications',
            'hospital_name', 'illness_name', 'user_name'
        ]
        read_only_fields = ['prescription_id']


class PrescriptionDetailSerializer(PrescriptionSerializer):
    medication_groups = MedicationGroupSerializer(source='group_prescription', many=True, read_only=True)

    class Meta(PrescriptionSerializer.Meta):
        fields = PrescriptionSerializer.Meta.fields + ['medication_groups']
    #
    # def get_medication_groups(self, obj):
    #     from .medication_group import MedicationGroupSerializer
    #     return MedicationGroupSerializer(obj.medication_groups.all(), many=True).data


# 처방전 생성용 시리얼라이저
class CreatePrescriptionSerializer(serializers.ModelSerializer):
    medications = PrescriptionMedicationSerializer(many=True, write_only=True)

    class Meta:
        model = Prescription
        fields = [
            'medical_info', 'prescription_date', 'medications'
        ]

    @transaction.atomic
    def create(self, validated_data):
        medications_data = validated_data.pop('medications')
        prescription = Prescription.objects.create(**validated_data)

        for medication_data in medications_data:
            PrescriptionMedication.objects.create(
                prescription=prescription,
                **medication_data
            )

        return prescription


# serializers.py
class SharedPrescriptionSerializer(serializers.ModelSerializer):
    """공유 처방전을 위한 시리얼라이저"""
    medical_conditions = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = ['prescription_id', 'prescription_date', 'medical_conditions', 'medications']

    def get_medical_conditions(self, obj):
        # 이 처방전과 연결된 모든 의료정보 조회
        medical_infos = UserMedicalInfo.objects.filter(prescription=obj)
        return [
            {
                'hospital': info.hospital.hosp_name,
                'illness': info.illness.ill_name,
                'is_primary': info.is_primary
            }
            for info in medical_infos
        ]



