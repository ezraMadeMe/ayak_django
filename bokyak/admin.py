from django.contrib import admin

from bokyak.models.prescription_medication import PrescriptionMedication, Prescription
from bokyak.models.medication_detail import MedicationDetail
from bokyak.models.medication_group import MedicationGroup
from bokyak.models.medication_alert import MedicationAlert
from bokyak.models.medication_record import MedicationRecord


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['prescription_id', 'prescription_date', 'is_active']
    list_filter = ['is_active', 'prescription_date']
    search_fields = ['prescription_id']

@admin.register(PrescriptionMedication)
class PrescriptionMedicationAdmin(admin.ModelAdmin):
    list_display = ['prescription', 'medication', 'duration_days', 'total_quantity']
    search_fields = ['prescription__prescription_id', 'medication__item_name']

@admin.register(MedicationGroup)
class MedicationGroupAdmin(admin.ModelAdmin):
    list_display = ['group_id', 'group_name', 'medical_info', 'reminder_enabled']
    list_filter = ['reminder_enabled']
    search_fields = ['group_name', 'medical_info__user__user_name']

@admin.register(MedicationDetail)
class MedicationDetailAdmin(admin.ModelAdmin):
    list_display = ['prescription_medication', 'actual_start_date', 'actual_end_date', 'remaining_quantity']
    list_filter = ['prescription_medication__prescription_id','actual_start_date']
    search_fields = ['prescription_medication__prescription_id', 'actual_start_date']

@admin.register(MedicationRecord)
class MedicationRecordAdmin(admin.ModelAdmin):
    list_display = ['medication_detail', 'record_type', 'record_date', 'quantity_taken']
    list_filter = ['record_type', 'record_date']
    search_fields = ['medication_detail__medication__item_name']

@admin.register(MedicationAlert)
class MedicationAlertAdmin(admin.ModelAdmin):
    list_display = ['medication_detail', 'alert_type', 'alert_time', 'is_active']
    list_filter = ['alert_type', 'is_active']
    search_fields = ['medication_detail__medication__item_name']