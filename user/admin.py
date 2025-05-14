from django.contrib import admin
from user.models import User, Hospital, Illness, MainIngredient, Medication

admin.site.register(User)
admin.site.register(Hospital)
admin.site.register(Illness)
admin.site.register(MainIngredient)
admin.site.register(Medication)