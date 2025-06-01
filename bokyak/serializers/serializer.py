from rest_framework import serializers

from bokyak.models.medication_alert import MedicationAlert
from bokyak.models.medication_cycle import MedicationCycle
from bokyak.models.medication_detail import MedicationDetail
from bokyak.models.medication_group import MedicationGroup
from bokyak.models.medication_record import MedicationRecord
from user.models.main_ingredient import MainIngredient


# MedicationGroup 관련 시리얼라이저
class MedicationGroupSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source='medical_info.hospital.hosp_name', read_only=True)
    illness_name = serializers.CharField(source='medical_info.illness.ill_name', read_only=True)

    class Meta:
        model = MedicationGroup
        fields = [
            'group_id', 'medical_info', 'prescription', 'group_name',
            'reminder_enabled', 'hospital_name', 'illness_name'
        ]
        read_only_fields = ['group_id']


# MedicationDetail 관련 시리얼라이저
class MedicationDetailSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication.item_name', read_only=True)
    medication_image = serializers.ImageField(source='medication.item_image', read_only=True)
    group_name = serializers.CharField(source='cycle.group.group_name', read_only=True)

    class Meta:
        model = MedicationDetail
        fields = [
            'id', 'cycle', 'medication', 'medication_name', 'medication_image',
            'dosage_pattern', 'is_active', 'remaining_quantity', 'group_name'
        ]


# MedicationCycle 관련 시리얼라이저
class MedicationCycleSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.group_name', read_only=True)

    class Meta:
        model = MedicationCycle
        fields = [
            'id', 'group', 'cycle_number', 'cycle_start',
            'cycle_end', 'is_active', 'group_name'
        ]
        read_only_fields = ['cycle_number']


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
    medication_name = serializers.CharField(source='medication_detail.medication.item_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)

    class Meta:
        model = MedicationRecord
        fields = [
            'id', 'medication_detail', 'record_type', 'record_type_display',
            'record_date', 'quantity_taken', 'notes', 'medication_name'
        ]


# MedicationAlert 관련 시리얼라이저
class MedicationAlertSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication_detail.medication.item_name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)

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


# 복합 시리얼라이저들 (상세 정보 포함)
class MedicationDetailWithRecordsSerializer(MedicationDetailSerializer):
    recent_records = serializers.SerializerMethodField()
    alerts = MedicationAlertSerializer(many=True, read_only=True)

    class Meta(MedicationDetailSerializer.Meta):
        fields = MedicationDetailSerializer.Meta.fields + ['recent_records', 'alerts']

    def get_recent_records(self, obj):
        recent_records = obj.records.order_by('-record_date')[:5]
        return MedicationRecordSerializer(recent_records, many=True).data


class MedicationCycleDetailSerializer(MedicationCycleSerializer):
    medication_details = MedicationDetailSerializer(many=True, read_only=True)

    class Meta(MedicationCycleSerializer.Meta):
        fields = MedicationCycleSerializer.Meta.fields + ['medication_details']


class MedicationGroupDetailSerializer(MedicationGroupSerializer):
    current_cycle = serializers.SerializerMethodField()
    cycles = MedicationCycleSerializer(many=True, read_only=True)

    class Meta(MedicationGroupSerializer.Meta):
        fields = MedicationGroupSerializer.Meta.fields + ['current_cycle', 'cycles']

    def get_current_cycle(self, obj):
        current_cycle = obj.cycles.filter(is_active=True).first()
        if current_cycle:
            return MedicationCycleDetailSerializer(current_cycle).data
        return None


# 복약 기록 생성용 시리얼라이저
class CreateMedicationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationRecord
        fields = [
            'medication_detail', 'record_type', 'record_date',
            'quantity_taken', 'notes'
        ]

    def create(self, validated_data):
        record = MedicationRecord.objects.create(**validated_data)

        # 복용 기록인 경우 잔여량 업데이트
        if record.record_type == MedicationRecord.RecordType.TAKEN:
            medication_detail = record.medication_detail
            medication_detail.remaining_quantity -= record.quantity_taken
            medication_detail.save()

        return record