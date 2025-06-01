# user/serializers/user.py
from rest_framework import serializers
from user.models.ayakuser import AyakUser

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AyakUser
        fields = ['user_id', 'user_name', 'join_date', 'push_agree', 'is_active']
        read_only_fields = ['join_date']