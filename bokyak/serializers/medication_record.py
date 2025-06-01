# bokyak/serializers/medication_record.py
from rest_framework import serializers
from bokyak.models.medication_record import MedicationRecord


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