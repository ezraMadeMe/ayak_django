from typing import Dict, Any, List
from django.db.models import Q

from user.models import Medication
from user.formatters import format_medication


class MedicationService:
    """약물 관리 서비스"""

    @staticmethod
    def search_medications(
        keyword: str = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """약물 검색"""
        query = Q()

        if keyword:
            query |= Q(medication_name__icontains=keyword)
            query |= Q(main_item_ingr__icontains=keyword)

        medications = Medication.objects.filter(query).order_by('medication_name')

        total_count = medications.count()
        medications = medications[offset:offset + limit]

        return {
            'total_count': total_count,
            'medications': [format_medication(medication) for medication in medications]
        }


    @staticmethod
    def get_medication_detail(medication_id: str) -> Dict[str, Any]:
        """약물 상세 정보 조회"""
        medication = Medication.objects.get(medication_id=medication_id)
        return format_medication(medication)

