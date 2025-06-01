# user/serializers/illness.py
from rest_framework import serializers
from user.models.illness import Illness


class IllnessSerializer(serializers.ModelSerializer):
    ill_type_display = serializers.CharField(source='get_ill_type_display', read_only=True)

    class Meta:
        model = Illness
        fields = [
            'illness_id', 'user', 'ill_type', 'ill_type_display',
            'ill_name', 'ill_code', 'ill_start', 'ill_end', 'is_chronic'
        ]
        read_only_fields = ['illness_id']