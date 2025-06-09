# bokyak/views/__init__.py
from .prescription import PrescriptionViewSet
from .medication_group import MedicationGroupViewSet
from .medication_detail import MedicationDetailViewSet
from .medication_record import MedicationRecordViewSet
from .medication_alert import MedicationAlertViewSet

__all__ = [
    'PrescriptionViewSet', 'MedicationGroupViewSet',
    'MedicationDetailViewSet', 'MedicationRecordViewSet', 'MedicationAlertViewSet'
]