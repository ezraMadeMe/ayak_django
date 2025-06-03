from rest_framework import serializers

from bokyak.serializers.medication_info_serializer import MedicationRecordSerializer, MedicationBasicSerializer


class MedicationItemDataSerializer(serializers.Serializer):
    medication_detail_id = serializers.IntegerField()
    medication = MedicationBasicSerializer()
    dosage_time = serializers.CharField()
    quantity_per_dose = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.CharField()
    special_instructions = serializers.CharField(allow_blank=True)
    is_taken_today = serializers.BooleanField()
    taken_at = serializers.DateTimeField(allow_null=True)
    record_type = serializers.CharField(allow_null=True)

class CompletionStatusSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    taken = serializers.IntegerField()
    completion_rate = serializers.FloatField()

class MedicationGroupDataSerializer(serializers.Serializer):
    group_id = serializers.CharField()
    group_name = serializers.CharField()
    cycle_id = serializers.IntegerField()
    cycle_number = serializers.IntegerField()
    dosage_times = serializers.ListField(child=serializers.CharField())
    medications_by_time = serializers.DictField()
    completion_status = serializers.DictField()

class OverallStatsSerializer(serializers.Serializer):
    total_medications = serializers.IntegerField()
    total_taken = serializers.IntegerField()
    total_missed = serializers.IntegerField()
    overall_completion_rate = serializers.FloatField()

class NextDosageDataSerializer(serializers.Serializer):
    next_dosage_time = serializers.CharField()
    target_date = serializers.DateField()
    medications = MedicationItemDataSerializer(many=True)
    total_count = serializers.IntegerField()

class BulkRecordResponseSerializer(serializers.Serializer):
    created_records = MedicationRecordSerializer(many=True)
    failed_records = serializers.ListField()
    total_requested = serializers.IntegerField()
    total_created = serializers.IntegerField()
    total_failed = serializers.IntegerField()

class TodayMedicationDataSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    today_date = serializers.DateField()
    medication_groups = MedicationGroupDataSerializer(many=True)
    overall_stats = OverallStatsSerializer()

