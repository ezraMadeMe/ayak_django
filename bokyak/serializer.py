from rest_framework import serializers

import user.serializer
from .models import BokyakGroup, Bokyak, BokyakRecord


class BokyakGroupSerializer(serializers.Serializer):
    class Meta:
        model = BokyakGroup
        fields = '__all__'


class BokyakCycleSerializer(serializers.Serializer):
    class Meta:
        model = BokyakGroup
        fields = ['user_id', 'group_name', 'rel_hosp', 'rel_ill']
    group_id = serializers.CharField()
    cycle_id = serializers.IntegerField()
    rel_hosp = serializers.CharField()
    cycle_start = serializers.DateTimeField()
    cycle_end = serializers.DateTimeField()


class BokyakSerializer(serializers.Serializer):
    class Meta:
        model = Bokyak
        fields = '__all__'

    bokyak_config = BokyakCycleSerializer(many=True)


class BokyakRecordSerializer(serializers.Serializer):
    class Meta:
        model = BokyakRecord
        fields = '__all__'

    bokyak_ill = user.serializer.IllnessSerializer(many=True)
