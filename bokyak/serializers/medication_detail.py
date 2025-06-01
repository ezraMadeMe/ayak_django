# bokyak/serializers/medication_detail.py
from rest_framework import serializers
from bokyak.models.medication_detail import MedicationDetail


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


class MedicationDetailWithRecordsSerializer(MedicationDetailSerializer):
    recent_records = serializers.SerializerMethodField()
    alerts = serializers.SerializerMethodField()

    class Meta(MedicationDetailSerializer.Meta):
        fields = MedicationDetailSerializer.Meta.fields + ['recent_records', 'alerts']

    def get_recent_records(self, obj):
        from .medication_record import MedicationRecordSerializer
        recent_records = obj.records.order_by('-record_date')[:5]
        return MedicationRecordSerializer(recent_records, many=True).data

    def get_alerts(self, obj):
        from .medication_alert import MedicationAlertSerializer
        return MedicationAlertSerializer(obj.alerts.all(), many=True).data
