# bokyak/serializers/medication_record.py
from rest_framework import serializers
from bokyak.models.medication_record import MedicationRecord


# === 1. 기본 시리얼라이저들 ===

class MedicationBasicSerializer(serializers.ModelSerializer):
    """약물 기본 정보"""
    class Meta:
        model = Medication
        fields = ['item_seq', 'item_name', 'entp_name', 'item_image',
                 'class_name', 'dosage_form', 'is_prescription']

class MedicationRecordSerializer(serializers.ModelSerializer):
    """복약 기록"""
    class Meta:
        model = MedicationRecord
        fields = ['id', 'medication_detail_id', 'record_type', 'record_date',
                 'quantity_taken', 'notes', 'created_at']

# === 2. 복합 시리얼라이저들 ===

class TodayDosageItemSerializer(serializers.Serializer):
    """오늘의 복약 아이템 (PillGrid용)"""
    medication_detail_id = serializers.IntegerField()
    medication = MedicationBasicSerializer()
    dosage_time = serializers.CharField()  # "morning", "lunch", "evening", "bedtime", "prn"
    quantity_per_dose = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.CharField()
    special_instructions = serializers.CharField(allow_blank=True)
    is_taken_today = serializers.BooleanField()
    taken_at = serializers.DateTimeField(allow_null=True)
    record_type = serializers.CharField(allow_null=True)  # 오늘의 기록 상태

class TodayMedicationGroupSerializer(serializers.Serializer):
    """오늘의 복약그룹"""
    group_id = serializers.CharField()
    group_name = serializers.CharField()
    cycle_id = serializers.IntegerField()
    cycle_number = serializers.IntegerField()
    dosage_times = serializers.ListField(
        child=serializers.CharField()
    )  # ["morning", "evening"]
    medications_by_time = serializers.DictField()  # {"morning": [...], "evening": [...]}
    completion_status = serializers.DictField()  # {"morning": {"total": 5, "taken": 3}, ...}

class HomeDataSerializer(serializers.Serializer):
    """홈화면 종합 데이터"""
    user_id = serializers.CharField()
    today_date = serializers.DateField()
    medication_groups = TodayMedicationGroupSerializer(many=True)
    overall_stats = serializers.DictField()  # 전체 통계
    urgent_notifications = serializers.ListField()
    upcoming_schedules = serializers.ListField()


class MedicationRecordSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication_detail.medication.item_name', read_only=True)
    record_type_display = serializers.CharField(source='get_record_type_display', read_only=True)

    class Meta:
        model = MedicationRecord
        fields = [
            'id', 'medication_detail', 'record_type', 'record_type_display',
            'record_date', 'quantity_taken', 'notes', 'medication_name'
        ]


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