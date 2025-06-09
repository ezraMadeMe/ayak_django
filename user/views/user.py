# user/views/user.py
import logging
import uuid
from django.utils import timezone
from pydantic.config import JsonEncoder
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from user.formatters import format_ayak_user
from user.models.ayakuser import AyakUser

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('social_login.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def generate_user_id():
    """고유한 사용자 ID 생성"""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_suffix = str(uuid.uuid4().hex)[:6].upper()
    return f"AYAK_{timestamp}_{random_suffix}"


def generate_token_for_user(user):
    """사용자를 위한 JWT 토큰 생성"""
    refresh = RefreshToken()
    refresh['user_id'] = user.user_id  # user_id를 토큰에 추가
    refresh['social_id'] = user.social_id
    refresh['social_provider'] = user.social_provider

    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh)
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def social_login(request):
    """소셜 로그인 처리"""
    logger.info(f"소셜 로그인 요청 데이터: {request.data}")
    try:
        social_id = request.data.get('social_id')
        social_provider = request.data.get('social_provider')
        user_name = request.data.get('user_name')
        email = request.data.get('email')
        profile_image = request.data.get('profile_image')

        if not social_id or not social_provider:
            return Response({
                'success': False,
                'message': 'social_id와 social_provider는 필수입니다.'
            }, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"소셜 로그인 시도: provider={social_provider}, social_id={social_id}")

        # 기존 사용자 확인
        try:
            user = AyakUser.objects.get(social_id=social_id)
            created = False
            # 기존 사용자 정보 업데이트
            if user_name:
                user.user_name = user_name
            if email:
                user.email = email
            if profile_image:
                user.profile_image_url = profile_image
            user.save()
        except AyakUser.DoesNotExist:
            # 새로운 사용자 생성
            user = AyakUser.objects.create(
                user_id=generate_user_id(),
                social_id=social_id,
                social_provider=social_provider,
                user_name=user_name or '',
                email=email,
                profile_image_url=profile_image
            )
            created = True

        # 토큰 생성
        tokens = generate_token_for_user(user)
        
        logger.info(f"{'새로운 사용자 생성' if created else '기존 사용자 로그인'}: user_id={user.user_id}")
        logger.info(f"tokens={tokens}")

        return Response({
            'success': True,
            'data': {
                'user': format_ayak_user(user),
                'tokens': tokens
            },
            'message': '회원가입 완료' if created else '로그인 성공'
        })

    except Exception as e:
        logger.error(f"소셜 로그인 처리 중 오류 발생: {str(e)}", exc_info=True)
        return Response({
            'success': False,
            'message': f'로그인 처리 중 오류가 발생했습니다: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """
    사용자 관리를 위한 ViewSet
    - 회원 정보 조회
    - 회원 정보 수정
    - 회원 탈퇴
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AyakUser.objects.filter(user_id=self.request.user.user_id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """현재 로그인한 사용자 정보 조회"""
        try:
            user = request.user
            return Response({
                'success': True,
                'data': {
                    'user_id': user.user_id,
                    'user_name': user.user_name,
                    'email': user.email,
                    'profile_image': user.profile_image_url,
                    'social_provider': user.social_provider
                }
            })
        except Exception as e:
            logger.error(f"사용자 정보 조회 중 오류 발생: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'사용자 정보 조회 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        """사용자 프로필 정보 수정"""
        try:
            user = request.user
            
            # 수정 가능한 필드 업데이트
            if 'user_name' in request.data:
                user.user_name = request.data['user_name']
            if 'email' in request.data:
                user.email = request.data['email']
            if 'profile_image' in request.data:
                user.profile_image_url = request.data['profile_image']
            
            user.save()

            return Response({
                'success': True,
                'data': {
                    'user_id': user.user_id,
                    'user_name': user.user_name,
                    'email': user.email,
                    'profile_image': user.profile_image_url
                },
                'message': '프로필이 성공적으로 수정되었습니다.'
            })
        except Exception as e:
            logger.error(f"프로필 수정 중 오류 발생: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'프로필 수정 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'])
    def deactivate(self, request):
        """회원 탈퇴 (계정 비활성화)"""
        try:
            user = request.user
            user.is_active = False
            user.save()

            return Response({
                'success': True,
                'message': '회원 탈퇴가 성공적으로 처리되었습니다.'
            })
        except Exception as e:
            logger.error(f"회원 탈퇴 처리 중 오류 발생: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'message': f'회원 탈퇴 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)