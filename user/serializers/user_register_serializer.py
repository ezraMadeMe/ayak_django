from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'user_id', 'user_name', 'email', 'password', 'confirm_password',
            'social_provider', 'social_id', 'profile_image_url',
            'phone_number', 'birth_date', 'gender',
            'push_agree', 'notification_enabled', 'marketing_agree'
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'user_id': {'read_only': True},  # 자동 생성
        }

    def validate(self, data):
        # 소셜 로그인이 아닌 경우 비밀번호 필수
        if not data.get('social_provider') and not data.get('password'):
            raise serializers.ValidationError("비밀번호는 필수입니다.")

        # 비밀번호 확인
        if data.get('password') and data.get('confirm_password'):
            if data['password'] != data['confirm_password']:
                raise serializers.ValidationError("비밀번호가 일치하지 않습니다.")

        # 이메일 중복 확인
        if data.get('email'):
            if User.objects.filter(email=data['email']).exists():
                raise serializers.ValidationError("이미 사용 중인 이메일입니다.")

        # 소셜 ID 중복 확인
        if data.get('social_provider') and data.get('social_id'):
            if User.objects.filter(
                    social_provider=data['social_provider'],
                    social_id=data['social_id']
            ).exists():
                raise serializers.ValidationError("이미 가입된 소셜 계정입니다.")

        return data

    def create(self, validated_data):
        # confirm_password 제거
        validated_data.pop('confirm_password', None)

        # 비밀번호 해시화
        password = validated_data.pop('password', None)

        # 사용자 생성
        user = User(**validated_data)

        if password:
            user.set_password(password)

        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    # 일반 로그인
    user_id = serializers.CharField(required=False)
    password = serializers.CharField(required=False)

    # 소셜 로그인
    social_provider = serializers.CharField(required=False)
    social_id = serializers.CharField(required=False)
    social_token = serializers.CharField(required=False)

    # 공통 정보
    user_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    profile_image_url = serializers.URLField(required=False)

    def validate(self, data):
        # 일반 로그인 또는 소셜 로그인 중 하나는 필수
        has_normal_login = data.get('user_id') and data.get('password')
        has_social_login = data.get('social_provider') and data.get('social_id')

        if not has_normal_login and not has_social_login:
            raise serializers.ValidationError(
                "일반 로그인 정보(user_id, password) 또는 소셜 로그인 정보(social_provider, social_id)가 필요합니다."
            )

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'user_id', 'user_name', 'email', 'profile_image_url',
            'phone_number', 'birth_date', 'gender',
            'push_agree', 'notification_enabled', 'marketing_agree',
            'join_date', 'last_login_date'
        ]
        read_only_fields = ['user_id', 'join_date']