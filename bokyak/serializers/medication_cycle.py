# bokyak/serializers/medication_cycle.py
from rest_framework import serializers
from bokyak.models.medication_cycle import MedicationCycle


class MedicationCycleSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.group_name', read_only=True)

    class Meta:
        model = MedicationCycle
        fields = [
            'id', 'group', 'cycle_number', 'cycle_start',
            'cycle_end', 'is_active', 'group_name'
        ]
        read_only_fields = ['cycle_number']


class MedicationCycleDetailSerializer(MedicationCycleSerializer):
    medication_details = serializers.SerializerMethodField()

    class Meta(MedicationCycleSerializer.Meta):
        fields = MedicationCycleSerializer.Meta.fields + ['medication_details']

    def get_medication_details(self, obj):
        from .medication_detail import MedicationDetailSerializer
        return MedicationDetailSerializer(obj.medication_details.all(), many=True).data
