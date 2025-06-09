from typing import Dict, Any, List, Optional
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from datetime import datetime

from bokyak.models import prescription, Prescription
from user.formatters import format_ayak_user, format_user_medical_info
from user.models import AyakUser, UserMedicalInfo, Hospital, Illness


class UserService:
    """사용자 관리 서비스"""

    @staticmethod
    def get_user_profile(user_id: str) -> Dict[str, Any]:
        """사용자 프로필 조회"""
        user = AyakUser.objects.get(user_id=user_id)
        return format_ayak_user(user)

    @staticmethod
    def update_user_profile(
        user_id: str,
        username: str = None,
        email: str = None,
        phone_number: str = None,
        birth_date: str = None,
        gender: str = None,
        profile_image: Any = None
    ) -> Dict[str, Any]:
        """사용자 프로필 수정"""
        user = AyakUser.objects.get(user_id=user_id)

        if username:
            user.username = username
        if email:
            user.email = email
        if phone_number:
            user.phone_number = phone_number
        if birth_date:
            user.birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        if gender:
            user.gender = gender
        if profile_image:
            user.profile_image = profile_image

        user.save()
        return format_ayak_user(user)

    @staticmethod
    def change_password(user_id: str, old_password: str, new_password: str) -> bool:
        """비밀번호 변경"""
        user = AyakUser.objects.get(user_id=user_id)
        
        if not user.check_password(old_password):
            raise ValueError("현재 비밀번호가 일치하지 않습니다.")
        
        user.set_password(new_password)
        user.save()
        return True

    @staticmethod
    def deactivate_account(user_id: str, password: str) -> bool:
        """계정 비활성화"""
        user = authenticate(user_id=user_id, password=password)
        if not user:
            raise ValueError("비밀번호가 일치하지 않습니다.")

        user.is_active = False
        user.save()
        return True

    @staticmethod
    def get_medical_info_list(user_id: str) -> List[Dict[str, Any]]:
        """사용자의 의료 정보 목록 조회"""
        medical_infos = UserMedicalInfo.objects.filter(
            user__user_id=user_id
        ).select_related(
            'user',
            'hospital',
            'illness'
        ).order_by('-prescription__prescription_date')

        return [format_user_medical_info(info) for info in medical_infos]

    @staticmethod
    def get_medical_info(user_id: str, medical_info_id: int) -> Dict[str, Any]:
        """특정 의료 정보 상세 조회"""
        medical_info = UserMedicalInfo.objects.get(
            id=medical_info_id,
            user__user_id=user_id
        )
        return format_user_medical_info(medical_info)

    @staticmethod
    @transaction.atomic
    def create_medical_info(
        user_id: str,
        hospital_id: str,
        illness_id: int
    ) -> Dict[str, Any]:
        """의료 정보 생성"""
        user = AyakUser.objects.get(user_id=user_id)
        hospital = Hospital.objects.get(hospital_id=hospital_id)
        illness = Illness.objects.get(illness_id=illness_id)

        medical_info = UserMedicalInfo.objects.create(
            user=user,
            hospital=hospital,
            illness=illness,
        )

        return format_user_medical_info(medical_info)

    @staticmethod
    @transaction.atomic
    def update_medical_info(
        user_id: str,
        medical_info_id: int,
        hospital_id: str = None,
        illness_id: int = None,
        is_primary: bool = None,
        start_date: str = None,
        end_date: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        """의료 정보 수정"""
        medical_info = UserMedicalInfo.objects.get(
            id=medical_info_id,
            user__user_id=user_id
        )

        if hospital_id:
            medical_info.hospital = Hospital.objects.get(hospital_id=hospital_id)
        if illness_id:
            medical_info.illness = Illness.objects.get(illness_id=illness_id)
        if prescription.prescription_id is None or prescription.is_active is False:
            medical_info.prescription = Prescription()

        medical_info.save()
        return format_user_medical_info(medical_info)

    @staticmethod
    def delete_medical_info(user_id: str, medical_info_id: int) -> bool:
        """의료 정보 삭제"""
        medical_info = UserMedicalInfo.objects.get(
            id=medical_info_id,
            user__user_id=user_id
        )
        
        if medical_info.is_primary:
            raise ValueError("기본 의료 정보는 삭제할 수 없습니다.")
        
        medical_info.delete()
        return True 