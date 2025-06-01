# bokyak/serializers/medication_group.py
from rest_framework import serializers
from bokyak.models.medication_group import MedicationGroup


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


class MedicationGroupDetailSerializer(MedicationGroupSerializer):
    current_cycle = serializers.SerializerMethodField()
    cycles = serializers.SerializerMethodField()

    class Meta(MedicationGroupSerializer.Meta):
        fields = MedicationGroupSerializer.Meta.fields + ['current_cycle', 'cycles']

    def get_current_cycle(self, obj):
        from .medication_cycle import MedicationCycleDetailSerializer
        current_cycle = obj.cycles.filter(is_active=True).first()
        if current_cycle:
            return MedicationCycleDetailSerializer(current_cycle).data
        return None

    def get_cycles(self, obj):
        from .medication_cycle import MedicationCycleSerializer
        return MedicationCycleSerializer(obj.cycles.all(), many=True).data
