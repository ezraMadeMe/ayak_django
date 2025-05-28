from rest_framework import serializers

import user.serializer
from bokyak.models import MedicationRecord, MedicationCycle, MedicationDetail, MedicationGroup, MedicationAlert
from user.models import MainIngredient


# MedicationGroup 관련 시리얼라이저
class MedicationGroupSerializer(serializers.ModelSerializer):
    medical_info_detail = user.UserMedicalInfoSerializer(source='medical_info', read_only=True)

    class Meta:
        model = MedicationGroup
        fields = [
            'group_id', 'medical_info', 'medical_info_detail',
            'group_name', 'is_active', 'created_at'
        ]
        read_only_fields = ['group_id', 'created_at']


class MedicationGroupListSerializer(serializers.ModelSerializer):
    """복약그룹 목록용 간단한 시리얼라이저"""
    hospital_name = serializers.CharField(source='medical_info.hospital.hosp_name', read_only=True)
    illness_name = serializers.CharField(source='medical_info.illness.ill_name', read_only=True)

    class Meta:
        model = MedicationGroup
        fields = ['group_id', 'group_name', 'hospital_name', 'illness_name', 'is_active']


# MedicationDetail 관련 시리얼라이저
class MedicationDetailSerializer(serializers.ModelSerializer):
    medication_info = user.MedicationListSerializer(source='medication', read_only=True)
    dosage_interval_display = serializers.CharField(source='get_dosage_interval_display', read_only=True)

    class Meta:
        model = MedicationDetail
        fields = [
            'id', 'medication', 'medication_info', 'dosage_interval',
            'dosage_interval_display', 'frequency_per_interval',
            'quantity_per_dose', 'total_prescribed', 'remaining_quantity',
            'unit', 'special_instructions'
        ]


# MedicationCycle 관련 시리얼라이저
class MedicationCycleSerializer(serializers.ModelSerializer):
    medication_details = MedicationDetailSerializer(many=True, read_only=True)
    group_info = MedicationGroupListSerializer(source='group', read_only=True)

    class Meta:
        model = MedicationCycle
        fields = [
            'id', 'group', 'group_info', 'cycle_number', 'cycle_start',
            'cycle_end', 'prescription_date', 'next_visit_date',
            'notes', 'medication_details', 'created_at'
        ]
        read_only_fields = ['cycle_number', 'created_at']


class MedicationCycleListSerializer(serializers.ModelSerializer):
    """복약사이클 목록용 간단한 시리얼라이저"""
    group_name = serializers.CharField(source='group.group_name', read_only=True)
    medication_count = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = MedicationCycle
        fields = [
            'id', 'cycle_number', 'group_name', 'cycle_start',
            'next_visit_date', 'medication_count', 'days_remaining'
        ]

    def get_medication_count(self, obj):
        return obj.medication_details.count()

    def get_days_remaining(self, obj):
        if obj.next_visit_date:
            from django.utils import timezone
            today = timezone.now().date()
            delta = obj.next_visit_date - today
            return delta.days
        return None


# MedicationRecord 관련 시리얼라이저
class MedicationRecordSerializer(serializers.ModelSerializer):
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)
    medication_name = serializers.CharField(source='medication_detail.medication.item_name', read_only=True)
    cycle_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MedicationRecord
        fields = [
            'id', 'cycle', 'medication_detail', 'record_type',
            'record_type_display', 'record_date', 'quantity_taken',
            'notes', 'symptoms', 'medication_name', 'cycle_info'
        ]

    def get_cycle_info(self, obj):
        return {
            'cycle_number': obj.cycle.cycle_number,
            'group_name': obj.cycle.group.group_name
        }


class MedicationRecordCreateSerializer(serializers.ModelSerializer):
    """복약기록 생성용 시리얼라이저"""

    class Meta:
        model = MedicationRecord
        fields = [
            'cycle', 'medication_detail', 'record_type',
            'record_date', 'quantity_taken', 'notes', 'symptoms'
        ]


# MedicationAlert 관련 시리얼라이저
class MedicationAlertSerializer(serializers.ModelSerializer):
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    medication_name = serializers.CharField(source='medication_detail.medication.item_name', read_only=True)

    class Meta:
        model = MedicationAlert
        fields = [
            'id', 'medication_detail', 'alert_type', 'alert_type_display',
            'alert_time', 'is_active', 'message', 'medication_name'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class IngredientSearchSerializer(serializers.ModelSerializer):
    """주성분 검색용 시리얼라이저"""
    medications_count = serializers.SerializerMethodField()

    class Meta:
        model = MainIngredient
        fields = [
            'ingr_code', 'display_name', 'main_ingr_name_en',
            'full_density_info', 'dosage_form', 'medications_count'
        ]

    def get_medications_count(self, obj):
        return obj.medication_uses.count()