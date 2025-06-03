from rest_framework import serializers

from bokyak.serializers import MedicationRecordSerializer
from bokyak.serializers.medication_data_serializer import MedicationBasicSerializer
from bokyak.serializers.medication_info_serializer import MedicationCycleSerializer, MedicationDetailSerializer, \
    MedicationAlertSerializer, MedicationGroupSerializer


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


class MedicationCycleDetailSerializer(MedicationCycleSerializer):
    medication_details = MedicationDetailSerializer(many=True, read_only=True)

    class Meta(MedicationCycleSerializer.Meta):
        fields = MedicationCycleSerializer.Meta.fields + ['medication_details']


# 복합 시리얼라이저들 (상세 정보 포함)
class MedicationDetailWithRecordsSerializer(MedicationDetailSerializer):
    recent_records = serializers.SerializerMethodField()
    alerts = MedicationAlertSerializer(many=True, read_only=True)

    class Meta(MedicationDetailSerializer.Meta):
        fields = MedicationDetailSerializer.Meta.fields + ['recent_records', 'alerts']

    def get_recent_records(self, obj):
        recent_records = obj.records.order_by('-record_date')[:5]
        return MedicationRecordSerializer(recent_records, many=True).data


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

