from django.contrib import admin
from bokyak.models import MedicationAlert, MedicationRecord, \
    MedicationDetail, MedicationCycle, MedicationGroup

admin.site.register(MedicationGroup)
admin.site.register(MedicationCycle)
admin.site.register(MedicationDetail)
admin.site.register(MedicationRecord)
admin.site.register(MedicationAlert)