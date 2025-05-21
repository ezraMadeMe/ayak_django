from django.contrib import admin
from user.models import User, Hospital, Illness, MainIngredient, Medication, UserInfo, MedInfo

admin.site.register(User)
admin.site.register(Hospital)
admin.site.register(Illness)
admin.site.register(MainIngredient)
admin.site.register(Medication)
admin.site.register(UserInfo)
admin.site.register(MedInfo)