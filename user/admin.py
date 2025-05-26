from django.contrib import admin
from user.models import User, Hospital, Illness, MainIngredient, Medication, MedicationIngredient, \
    IngredientClassification, IngredientAlias, UserMedicalInfo

admin.site.register(User)
admin.site.register(Hospital)
admin.site.register(Illness)
admin.site.register(MainIngredient)
admin.site.register(IngredientAlias)
admin.site.register(IngredientClassification)
admin.site.register(MedicationIngredient)
admin.site.register(Medication)
admin.site.register(UserMedicalInfo)