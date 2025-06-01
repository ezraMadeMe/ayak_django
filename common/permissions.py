# common/permissions.py
from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    소유자만 수정 가능, 읽기는 모든 인증된 사용자
    """

    def has_object_permission(self, request, view, obj):
        # 읽기 권한은 모든 인증된 사용자에게
        if request.method in permissions.SAFE_METHODS:
            return True

        # 쓰기 권한은 소유자에게만
        return obj.user == request.user


class IsMedicalInfoOwner(permissions.BasePermission):
    """
    의료 정보 소유자만 접근 가능
    """

    def has_object_permission(self, request, view, obj):
        # 객체의 의료 정보 소유자 확인
        if hasattr(obj, 'medical_info'):
            return obj.medical_info.user == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'cycle'):
            return obj.cycle.group.medical_info.user == request.user
        elif hasattr(obj, 'medication_detail'):
            return obj.medication_detail.cycle.group.medical_info.user == request.user

        return False