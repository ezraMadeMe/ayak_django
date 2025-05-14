from django.contrib import admin
from bokyak.models import Bokyak, BokyakRecord, BokyakGroup, BokyakCycle

admin.site.register(Bokyak)
admin.site.register(BokyakGroup)
admin.site.register(BokyakRecord)
admin.site.register(BokyakCycle)