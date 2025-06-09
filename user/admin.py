from django.contrib import admin

from user.models.cache import HospitalCache, DiseaseCache
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
    search_fields = ['hosp_name', 'doctor_name', 'user__user_nickname']

@admin.register(Illness)
class IllnessAdmin(admin.ModelAdmin):
    list_display = ['illness_id', 'ill_name', 'ill_type', 'is_chronic', 'user']
    list_filter = ['ill_type', 'is_chronic']
    search_fields = ['ill_name', 'user__user_nickname']

@admin.register(MainIngredient)
class MainIngredientAdmin(admin.ModelAdmin):
    list_display = ['ingr_code', 'main_ingr_name_kr', 'main_ingr_name_en', 'is_combination_drug', 'atc_code']
    list_filter = ['is_combination_drug']
    search_fields = ['main_ingr_name_kr', 'main_ingr_name_en', 'ingr_code','combination_group']

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ['medication_id', 'medication_name', 'manufacturer']
    list_filter = ['medication_name']
    search_fields = ['medication_name','main_ingr_eng']

@admin.register(UserMedicalInfo)
class UserMedicalInfoAdmin(admin.ModelAdmin):
    list_display = ['user', 'hospital', 'illness', 'prescription']
    list_filter = ['hospital', 'illness']
    search_fields = ['user__user_nickname', 'hospital__hosp_name', 'illness__ill_name']

@admin.register(MedicationIngredient)
class MedicationIngredientAdmin(admin.ModelAdmin):
    list_display = ['medication', 'main_ingredient', 'amount', 'unit']
    list_filter = ['main_ingredient', 'is_main']
    search_fields = ['medication__medication_name', 'main_ingredient__main_ingr_name_kr', 'amount', 'unit']

@admin.register(HospitalCache)
class HospitalCacheAdmin(admin.ModelAdmin):
    list_display = ['hospital_code', 'hospital_name', 'hospital_type_name', 'sido_name']
    list_filter = ['hospital_name', 'sido_name']
    search_fields = ['hospital_name', 'hospital_type_name', 'sido_name', 'sigungu_name']

@admin.register(DiseaseCache)
class DiseaseCacheAdmin(admin.ModelAdmin):
    list_display = ['disease_code', 'disease_name_kr', 'disease_name_en']
    list_filter = ['disease_code', 'disease_name_kr']
    search_fields = ['disease_code', 'disease_name_kr', 'disease_name_en']

