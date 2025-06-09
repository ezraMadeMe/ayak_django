from typing import Dict, Any, List
from django.db.models import Q

from user.models import Illness
from user.formatters import format_illness


class IllnessService:
    """질병 관리 서비스"""

    @staticmethod
    def search_illnesses(
        keyword: str = None,
        category: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """질병 검색"""
        query = Q()

        if keyword:
            query |= Q(name__icontains=keyword)
            query |= Q(description__icontains=keyword)

        if category:
            query &= Q(category=category)

        illnesses = Illness.objects.filter(query).order_by('name')

        total_count = illnesses.count()
        illnesses = illnesses[offset:offset + limit]

        return {
            'total_count': total_count,
            'illnesses': [format_illness(illness) for illness in illnesses]
        }

    @staticmethod
    def get_illness_detail(illness_id: int) -> Dict[str, Any]:
        """질병 상세 정보 조회"""
        illness = Illness.objects.get(id=illness_id)
        return format_illness(illness)

    @staticmethod
    def search_by_name(
        name: str,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """질병명으로 검색"""
        illnesses = Illness.objects.filter(
            ill_name__icontains=name
        ).order_by('name')

        total_count = illnesses.count()
        illnesses = illnesses[offset:offset + limit]

        return {
            'total_count': total_count,
            'illnesses': [format_illness(illness) for illness in illnesses]
        } 