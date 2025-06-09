from typing import Dict, Any
from django.db.models import Q

from user.models import Hospital, HospitalCache
from user.formatters import format_hospital


class HospitalService:
    """병원 관리 서비스"""

    @staticmethod
    def search_hospitals(
        keyword: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        등록할 병원 검색
        HospitalCache 에서 없으면 API 호출
        :param keyword: 병원 이름
        """
        query = Q()

        # 키워드 검색
        if keyword:
            query |= Q(hospital_name__icontains=keyword)

        # 기본 쿼리셋
        hospitals = HospitalCache.objects.filter(query)

        # 페이지네이션
        total_count = hospitals.count()
        hospitals = hospitals[offset:offset + limit]

        return {
            'total_count': total_count,
            'hospitals': [format_hospital(hospital) for hospital in hospitals]
        }

    @staticmethod
    def search_by_name(
        name: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """병원명으로 검색"""
        hospitals = Hospital.objects.filter(
            hosp_name__icontains=name
        ).order_by('hosp_name')

        total_count = hospitals.count()
        hospitals = hospitals[offset:offset + limit]

        return {
            'total_count': total_count,
            'hospitals': [format_hospital(hospital) for hospital in hospitals]
        }
