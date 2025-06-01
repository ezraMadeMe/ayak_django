# user/views/__init__.py
from .user import UserViewSet
from .hospital import HospitalViewSet
from .illness import IllnessViewSet
from .medication import MedicationViewSet, MainIngredientViewSet
from .medical_info import UserMedicalInfoViewSet

__all__ = [
    'UserViewSet', 'HospitalViewSet', 'IllnessViewSet',
    'MedicationViewSet', 'MainIngredientViewSet', 'UserMedicalInfoViewSet'
]
