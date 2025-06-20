from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
import logging
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from user.services.user_register_service import UserService

User = get_user_model()
logger = logging.getLogger(__name__)

def validate_registration_data(data):
    errors = {}
    required_fields = ['user_name', 'email', 'password', 'confirm_password']
    
    # 필수 필드 검증
    for field in required_fields:
        if not data.get(field):
            errors[field] = f"{field}는 필수 입력 항목입니다."
    
    if errors:
        return errors
    
    # 이메일 형식 검증
    try:
        validate_email(data['email'])
    except ValidationError:
        errors['email'] = "유효한 이메일 주소를 입력해주세요."
    
    # 이메일 중복 검증
    if User.objects.filter(email=data['email']).exists():
        errors['email'] = "이미 사용 중인 이메일입니다."
    
    # 비밀번호 일치 검증
    if data['password'] != data['confirm_password']:
        errors['password'] = "비밀번호가 일치하지 않습니다."
    
    return errors

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """
    사용자 회원가입 API

    Request Body:
    {
        "user_name": "홍길동",
        "email": "user@example.com",
        "password": "password123",
        "confirm_password": "password123",
        "phone_number": "010-1234-5678",
        "birth_date": "1990-01-01",
        "gender": "M",
        "push_agree": true,
        "notification_enabled": true,
        "marketing_agree": false
    }
    """
    try:
        # 데이터 검증
        validation_errors = validate_registration_data(request.data)
        if validation_errors:
            return Response({
                'success': False,
                'message': '입력 데이터가 올바르지 않습니다.',
                'errors': validation_errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # 회원가입 처리
        with transaction.atomic():
            user_data = {
                'user_name': request.data['user_name'],
                'email': request.data['email'],
                'password': request.data['password'],
                'phone_number': request.data.get('phone_number'),
                'birth_date': request.data.get('birth_date'),
                'gender': request.data.get('gender'),
                'push_agree': request.data.get('push_agree', False),
                'notification_enabled': request.data.get('notification_enabled', False),
                'marketing_agree': request.data.get('marketing_agree', False)
            }
            result = UserService.register_user(user_data)

        # 사용자 데이터 준비
        user_data = {
            'user_id': result['user'].user_id,
            'user_name': result['user'].user_name,
            'email': result['user'].email,
            'phone_number': result['user'].phone_number,
            'birth_date': result['user'].birth_date,
            'gender': result['user'].gender,
            'push_agree': result['user'].push_agree,
            'notification_enabled': result['user'].notification_enabled,
            'marketing_agree': result['user'].marketing_agree,
            'created_at': result['user'].created_at.isoformat() if result['user'].created_at else None,
            'updated_at': result['user'].updated_at.isoformat() if result['user'].updated_at else None
        }

        logger.info(f"새 사용자 회원가입: {result['user'].user_id}")

        return Response({
            'success': True,
            'message': '회원가입이 완료되었습니다.',
            'data': {
                'user': user_data,
                'access_token': result['access_token'],
                'refresh_token': result['refresh_token'],
                'is_new_user': result['is_new_user']
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"회원가입 실패: {str(e)}")
        return Response({
            'success': False,
            'message': f'회원가입 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def validate_login_data(data):
    errors = {}
    
    # 소셜 로그인
    if data.get('social_provider'):
        required_fields = ['social_provider', 'social_id', 'social_token']
        for field in required_fields:
            if not data.get(field):
                errors[field] = f"{field}는 필수 입력 항목입니다."
    # 일반 로그인
    else:
        if not data.get('user_id'):
            errors['user_id'] = "사용자 ID는 필수 입력 항목입니다."
        if not data.get('password'):
            errors['password'] = "비밀번호는 필수 입력 항목입니다."
    
    return errors

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """
    사용자 로그인 API (일반 로그인 + 소셜 로그인)

    일반 로그인 Request Body:
    {
        "user_id": "AYAK_20240601_ABC123",
        "password": "password123"
    }

    소셜 로그인 Request Body:
    {
        "social_provider": "google",
        "social_id": "google_user_unique_id",
        "social_token": "google_access_token",
        "user_name": "홍길동",
        "email": "user@gmail.com",
        "profile_image_url": "https://example.com/profile.jpg"
    }
    """
    try:
        # 데이터 검증
        validation_errors = validate_login_data(request.data)
        if validation_errors:
            return Response({
                'success': False,
                'message': '로그인 정보가 올바르지 않습니다.',
                'errors': validation_errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # 로그인 처리
        with transaction.atomic():
            result = UserService.login_user(request.data)

        # 사용자 데이터 준비
        user_data = {
            'user_id': result['user'].user_id,
            'user_name': result['user'].user_name,
            'email': result['user'].email,
            'phone_number': result['user'].phone_number,
            'birth_date': result['user'].birth_date,
            'gender': result['user'].gender,
            'push_agree': result['user'].push_agree,
            'notification_enabled': result['user'].notification_enabled,
            'marketing_agree': result['user'].marketing_agree,
            'created_at': result['user'].created_at.isoformat() if result['user'].created_at else None,
            'updated_at': result['user'].updated_at.isoformat() if result['user'].updated_at else None
        }

        login_type = "소셜 로그인" if request.data.get('social_provider') else "일반 로그인"
        user_status = "신규 사용자" if result['is_new_user'] else "기존 사용자"

        if login_type == "소셜 로그인":
            user_data.setdefault('social_id', result['user'].social_id)
            user_data.setdefault('social_token', result['user'].social_token)
            user_data.setdefault('social_provider', result['user'].social_provider)

        logger.info(f"{login_type} 성공: {result['user'].user_id} ({user_status})")

        return Response({
            'success': True,
            'message': f'{login_type} 성공',
            'data': {
                'user': user_data,
                'access_token': result['access_token'],
                'refresh_token': result['refresh_token'],
                'is_new_user': result['is_new_user']
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"로그인 실패: {str(e)}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """
    사용자 프로필 조회 API
    """
    try:
        user = request.user
        user_data = {
            'user_id': user.user_id,
            'user_name': user.user_name,
            'email': user.email,
            'phone_number': user.phone_number,
            'birth_date': user.birth_date,
            'gender': user.gender,
            'push_agree': user.push_agree,
            'notification_enabled': user.notification_enabled,
            'marketing_agree': user.marketing_agree,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None
        }

        return Response({
            'success': True,
            'message': '사용자 프로필 조회 성공',
            'data': user_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"프로필 조회 실패: {str(e)}")
        return Response({
            'success': False,
            'message': f'프로필 조회 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def validate_profile_update_data(data):
    errors = {}
    
    if 'email' in data:
        try:
            validate_email(data['email'])
        except ValidationError:
            errors['email'] = "유효한 이메일 주소를 입력해주세요."
    
    return errors

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    """
    사용자 프로필 업데이트 API

    Request Body:
    {
        "user_name": "새이름",
        "email": "new@example.com",
        "phone_number": "010-9876-5432",
        "push_agree": false,
        "notification_enabled": false
    }
    """
    try:
        user = request.user
        
        # 데이터 검증
        validation_errors = validate_profile_update_data(request.data)
        if validation_errors:
            return Response({
                'success': False,
                'message': '입력 데이터가 올바르지 않습니다.',
                'errors': validation_errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # 프로필 업데이트
        with transaction.atomic():
            updated_user = UserService.update_user_profile(user, request.data)

        # 업데이트된 사용자 데이터 준비
        user_data = {
            'user_id': updated_user.user_id,
            'user_name': updated_user.user_name,
            'email': updated_user.email,
            'phone_number': updated_user.phone_number,
            'birth_date': updated_user.birth_date,
            'gender': updated_user.gender,
            'push_agree': updated_user.push_agree,
            'notification_enabled': updated_user.notification_enabled,
            'marketing_agree': updated_user.marketing_agree,
            'created_at': updated_user.created_at.isoformat() if updated_user.created_at else None,
            'updated_at': updated_user.updated_at.isoformat() if updated_user.updated_at else None
        }

        logger.info(f"사용자 프로필 업데이트: {user.user_id}")

        return Response({
            'success': True,
            'message': '프로필이 업데이트되었습니다.',
            'data': user_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"프로필 업데이트 실패: {str(e)}")
        return Response({
            'success': False,
            'message': f'프로필 업데이트 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """
    사용자 로그아웃 API

    Request Body:
    {
        "refresh_token": "refresh_token_string"
    }
    """
    try:
        refresh_token = request.data.get('refresh_token')

        if refresh_token:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                token = RefreshToken(refresh_token)
                token.blacklist()  # 토큰 블랙리스트 처리
            except Exception as e:
                logger.warning(f"토큰 블랙리스트 처리 실패: {str(e)}")

        logger.info(f"사용자 로그아웃: {request.user.user_id}")

        return Response({
            'success': True,
            'message': '로그아웃되었습니다.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"로그아웃 실패: {str(e)}")
        return Response({
            'success': False,
            'message': f'로그아웃 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def deactivate_user(request):
    """
    사용자 계정 비활성화 API

    Request Body:
    {
        "password": "current_password",  // 일반 회원만 필요
        "reason": "탈퇴 사유"
    }
    """
    try:
        user = request.user

        # 일반 회원인 경우 비밀번호 확인
        if not user.social_provider:
            password = request.data.get('password')
            if not password:
                return Response({
                    'success': False,
                    'message': '비밀번호를 입력해주세요.'
                }, status=status.HTTP_400_BAD_REQUEST)

            if not user.check_password(password):
                return Response({
                    'success': False,
                    'message': '비밀번호가 올바르지 않습니다.'
                }, status=status.HTTP_400_BAD_REQUEST)

        # 계정 비활성화
        with transaction.atomic():
            UserService.deactivate_user(user)

        reason = request.data.get('reason', '사용자 요청')
        logger.info(f"사용자 계정 비활성화: {user.user_id}, 사유: {reason}")

        return Response({
            'success': True,
            'message': '계정이 비활성화되었습니다.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"계정 비활성화 실패: {str(e)}")
        return Response({
            'success': False,
            'message': f'계정 비활성화 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def check_user_exists(request):
    """
    사용자 존재 여부 확인 API (중복 확인용)

    Request Body:
    {
        "email": "user@example.com",
        "social_provider": "google",
        "social_id": "google_user_id"
    }
    """
    try:
        email = request.data.get('email')
        social_provider = request.data.get('social_provider')
        social_id = request.data.get('social_id')

        exists_data = {}

        # 이메일 중복 확인
        if email:
            email_exists = User.objects.filter(email=email).exists()
            exists_data['email_exists'] = email_exists

        # 소셜 계정 중복 확인
        if social_provider and social_id:
            social_exists = User.objects.filter(
                social_provider=social_provider,
                social_id=social_id
            ).exists()
            exists_data['social_exists'] = social_exists

        return Response({
            'success': True,
            'message': '사용자 존재 여부 확인 완료',
            'data': exists_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"사용자 존재 확인 실패: {str(e)}")
        return Response({
            'success': False,
            'message': f'확인 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# URL 추가 (urls.py에 추가할 패턴)
"""
# auth_urls.py 또는 main urls.py에 추가
from django.urls import path
from . import views

auth_urlpatterns = [
    # 사용자 인증
    path('auth/register/', views.register_user, name='register_user'),
    path('auth/login/', views.login_user, name='login_user'),
    path('auth/logout/', views.logout_user, name='logout_user'),

    # 사용자 프로필
    path('auth/profile/', views.get_user_profile, name='get_user_profile'),
    path('auth/profile/update/', views.update_user_profile, name='update_user_profile'),

    # 계정 관리
    path('auth/deactivate/', views.deactivate_user, name='deactivate_user'),
    path('auth/check-exists/', views.check_user_exists, name='check_user_exists'),
]
"""