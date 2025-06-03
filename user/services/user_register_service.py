from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone

import requests
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserService:

    @staticmethod
    def register_user(validated_data):
        """사용자 회원가입"""
        try:
            user = User.objects.create_user(**validated_data)

            # JWT 토큰 생성
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            return {
                'user': user,
                'access_token': access_token,
                'refresh_token': refresh_token,
                'is_new_user': True
            }

        except Exception as e:
            raise Exception(f"회원가입 실패: {str(e)}")

    @staticmethod
    def login_user(validated_data):
        """사용자 로그인 (일반 + 소셜)"""
        try:
            # 소셜 로그인인 경우
            if validated_data.get('social_provider'):
                return UserService._social_login(validated_data)

            # 일반 로그인인 경우
            else:
                return UserService._normal_login(validated_data)

        except Exception as e:
            raise Exception(f"로그인 실패: {str(e)}")

    @staticmethod
    def _normal_login(data):
        """일반 로그인"""
        user = authenticate(
            username=data['user_id'],
            password=data['password']
        )

        if not user:
            raise Exception("아이디 또는 비밀번호가 올바르지 않습니다.")

        if not user.is_active:
            raise Exception("비활성화된 계정입니다.")

        # 마지막 로그인 시간 업데이트
        user.last_login_date = timezone.now()
        user.save(update_fields=['last_login_date'])

        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)

        return {
            'user': user,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'is_new_user': False
        }

    @staticmethod
    def _social_login(data):
        """소셜 로그인"""
        social_provider = data['social_provider']
        social_id = data['social_id']

        # 소셜 토큰 검증 (선택사항)
        if data.get('social_token'):
            UserService._verify_social_token(social_provider, data['social_token'])

        # 기존 사용자 찾기
        try:
            user = User.objects.get(
                social_provider=social_provider,
                social_id=social_id
            )

            # 정보 업데이트
            updated = False
            if data.get('user_name') and user.user_name != data['user_name']:
                user.user_name = data['user_name']
                updated = True

            if data.get('email') and user.email != data['email']:
                user.email = data['email']
                updated = True

            if data.get('profile_image_url') and user.profile_image_url != data['profile_image_url']:
                user.profile_image_url = data['profile_image_url']
                updated = True

            user.last_login_date = timezone.now()
            updated = True

            if updated:
                user.save()

            is_new_user = False

        except User.DoesNotExist:
            # 신규 사용자 생성
            user_data = {
                'user_name': data.get('user_name', ''),
                'email': data.get('email', ''),
                'social_provider': social_provider,
                'social_id': social_id,
                'profile_image_url': data.get('profile_image_url', ''),
                'last_login_date': timezone.now(),
            }

            user = User.objects.create(**user_data)
            is_new_user = True

        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)

        return {
            'user': user,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'is_new_user': is_new_user
        }

    @staticmethod
    def _verify_social_token(provider, token):
        """소셜 로그인 토큰 검증"""
        try:
            if provider == 'google':
                response = requests.get(
                    f'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={token}'
                )
                if response.status_code != 200:
                    raise Exception("유효하지 않은 Google 토큰입니다.")

            elif provider == 'kakao':
                response = requests.get(
                    'https://kapi.kakao.com/v1/user/access_token_info',
                    headers={'Authorization': f'Bearer {token}'}
                )
                if response.status_code != 200:
                    raise Exception("유효하지 않은 Kakao 토큰입니다.")

            # Apple, Facebook 등 다른 소셜 로그인 검증 로직 추가 가능

        except requests.RequestException:
            raise Exception(f"{provider} 토큰 검증 중 오류가 발생했습니다.")

    @staticmethod
    def update_user_profile(user, validated_data):
        """사용자 프로필 업데이트"""
        for field, value in validated_data.items():
            setattr(user, field, value)

        user.updated_at = timezone.now()
        user.save()

        return user

    @staticmethod
    def deactivate_user(user):
        """사용자 계정 비활성화"""
        user.is_active = False
        user.updated_at = timezone.now()
        user.save()

        return user