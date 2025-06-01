from django.contrib import admin
from user.models.user_medical_info import AyakUser, Hospital, Illness, UserMedicalInfo
from user.models.main_ingredient import MainIngredient
from user.models.medication import Medication
from user.models.medication_ingredient import MedicationIngredient


@admin.register(AyakUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'user_name', 'join_date', 'push_agree', 'is_active']
    list_filter = ['push_agree', 'is_active', 'join_date']
    search_fields = ['user_id', 'user_name']

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ['hospital_id', 'hosp_name', 'doctor_name', 'user']
    list_filter = ['hosp_type']
    search_fields = ['hosp_name', 'doctor_name', 'user__user_name']

@admin.register(Illness)
class IllnessAdmin(admin.ModelAdmin):
    list_display = ['illness_id', 'ill_name', 'ill_type', 'is_chronic', 'user']
    list_filter = ['ill_type', 'is_chronic']
    search_fields = ['ill_name', 'user__user_name']

@admin.register(MainIngredient)
class MainIngredientAdmin(admin.ModelAdmin):
    list_display = ['ingr_code', 'main_ingr_name_kr', 'main_ingr_name_en', 'is_combination', 'data_quality_score']
    list_filter = ['is_combination', 'is_active', 'dosage_form']
    search_fields = ['main_ingr_name_kr', 'main_ingr_name_en', 'original_code']

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ['item_seq', 'item_name', 'entp_name', 'is_prescription']
    list_filter = ['is_prescription', 'class_name']
    search_fields = ['item_name', 'entp_name']

@admin.register(UserMedicalInfo)
class UserMedicalInfoAdmin(admin.ModelAdmin):
    list_display = ['user', 'hospital', 'illness', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['user__user_name', 'hospital__hosp_name', 'illness__ill_name']

@admin.register(MedicationIngredient)
class MedicationIngredientAdmin(admin.ModelAdmin):
    list_display = ['medication', 'ingredient', 'content_amount', 'content_unit']
    list_filter = ['medication', 'ingredient']
    search_fields = ['medication__item_seq', 'ingredient__main_ingr_name_kr', 'content_amount', 'content_unit']
