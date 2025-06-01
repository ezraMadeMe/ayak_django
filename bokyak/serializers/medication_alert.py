# bokyak/serializers/medication_alert.py
from rest_framework import serializers
from bokyak.models.medication_alert import MedicationAlert


class MedicationAlertSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication_detail.medication.item_name', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)

    class Meta:
        model = MedicationAlert
        fields = [
            'id', 'medication_detail', 'alert_type', 'alert_type_display',
            'alert_time', 'is_active', 'message', 'medication_name'
        ]