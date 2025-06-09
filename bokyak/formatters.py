from typing import Optional, Dict, Any, List



def format_prescription(prescription) -> Dict[str, Any]:
    """처방전 정보 포맷팅"""
    return {
        'prescription_id': prescription.prescription_id,
        'prescription_count': prescription.prescription_count,
        'prescription_date': prescription.prescription_date.isoformat() if prescription.prescription_date else None,
        'previous_prescription': format_prescription(prescription.previous_prescription) if prescription.previous_prescription else None,
        'is_active': prescription.is_active,
        'created_at': prescription.created_at.isoformat() if prescription.created_at else None,
        'updated_at': prescription.updated_at.isoformat() if prescription.updated_at else None,
    }


def format_prescription_medication(prescription_med) -> Dict[str, Any]:
    """처방 의약품 정보 포맷팅"""
    # 순환 참조를 피하기 위해 간단한 형태로 포맷팅
    return {
        'id': prescription_med.id,
        'prescription': format_prescription(prescription_med.prescription) if prescription_med.prescription else None,
        'medication': {
            'medication_id': prescription_med.medication.medication_id,
            'medication_name': prescription_med.medication.medication_name,
            'manufacturer': prescription_med.medication.manufacturer,
        } if prescription_med.medication else None,
        'standard_dosage_pattern': prescription_med.standard_dosage_pattern,
        'patient_dosage_pattern': prescription_med.patient_dosage_pattern,
        'duration_days': prescription_med.duration_days,
        'total_quantity': float(prescription_med.total_quantity) if prescription_med.total_quantity else None,
        'source_prescription': format_prescription(prescription_med.source_prescription) if prescription_med.source_prescription else None,
        'created_at': prescription_med.created_at.isoformat() if prescription_med.created_at else None,
        'updated_at': prescription_med.updated_at.isoformat() if prescription_med.updated_at else None,
    }


def format_medication_group(group) -> Dict[str, Any]:
    """복약 그룹 정보 포맷팅"""
    return {
        'group_id': group.group_id,
        'medical_info': {
            'id': group.medical_info.id,
            'hospital': {
                'hospital_id': group.medical_info.hospital.hospital_id,
                'hosp_name': group.medical_info.hospital.hosp_name,
                'doctor_name': group.medical_info.hospital.doctor_name,
            } if group.medical_info.hospital else None,
            'illness': {
                'illness_id': group.medical_info.illness.illness_id,
                'ill_name': group.medical_info.illness.ill_name,
                'ill_type': group.medical_info.illness.ill_type,
            } if group.medical_info.illness else None,
        } if group.medical_info else None,
        'group_name': group.group_name,
        'reminder_enabled': group.reminder_enabled,
        'created_at': group.created_at.isoformat() if group.created_at else None,
        'updated_at': group.updated_at.isoformat() if group.updated_at else None,
    }


def format_medication_detail(detail) -> Dict[str, Any]:
    """복약 상세 정보 포맷팅"""
    return {
        'id': detail.id,
        'group': format_medication_group(detail.group) if detail.group else None,
        'prescription_medication': format_prescription_medication(detail.prescription_medication) if detail.prescription_medication else None,
        'actual_dosage_pattern': detail.actual_dosage_pattern,
        'actual_start_date': detail.actual_start_date.isoformat() if detail.actual_start_date else None,
        'actual_end_date': detail.actual_end_date.isoformat() if detail.actual_end_date else None,
        'remaining_quantity': detail.remaining_quantity,
        'patient_adjustments': detail.patient_adjustments,
        'created_at': detail.created_at.isoformat() if detail.created_at else None,
        'updated_at': detail.updated_at.isoformat() if detail.updated_at else None,
    }


def format_medication_alert(alert) -> Dict[str, Any]:
    """복약 알림 정보 포맷팅"""
    return {
        'id': alert.id,
        'medication_detail': format_medication_detail(alert.medication_detail) if alert.medication_detail else None,
        'alert_type': alert.alert_type,
        'alert_time': alert.alert_time.strftime('%H:%M:%S') if alert.alert_time else None,
        'is_active': alert.is_active,
        'message': alert.message,
        'created_at': alert.created_at.isoformat() if alert.created_at else None,
        'updated_at': alert.updated_at.isoformat() if alert.updated_at else None,
    }


def format_medication_record(record) -> Dict[str, Any]:
    """복약 기록 정보 포맷팅"""
    return {
        'id': record.id,
        'medication_detail': format_medication_detail(record.medication_detail) if record.medication_detail else None,
        'record_type': record.record_type,
        'record_date': record.record_date.isoformat() if record.record_date else None,
        'quantity_taken': float(record.quantity_taken) if record.quantity_taken else None,
        'notes': record.notes,
        'effectiveness_score': record.effectiveness_score,
        'tags': record.tags,
        'created_at': record.created_at.isoformat() if record.created_at else None,
        'updated_at': record.updated_at.isoformat() if record.updated_at else None,
    }


def format_today_medications(data) -> Dict[str, Any]:
    """오늘의 복약 데이터 포맷팅"""
    return {
        'date': data['date'].isoformat() if data.get('date') else None,
        'medication_groups': [
            {
                'group_id': group['group_id'],
                'group_name': group['group_name'],
                'medications_by_time': {
                    time_slot: [format_medication_detail(med) for med in meds]
                    for time_slot, meds in group['medications_by_time'].items()
                }
            }
            for group in data['medication_groups']
        ]
    }


def format_bulk_record_response(data) -> Dict[str, Any]:
    """복수 복약 기록 응답 포맷팅"""
    return {
        'created_records': [format_medication_record(record) for record in data['created_records']],
        'failed_records': data['failed_records'],
        'total_requested': data['total_requested'],
        'total_created': data['total_created'],
        'total_failed': data['total_failed']
    }


def format_api_response(success: bool, data: Any = None, message: str = None) -> Dict[str, Any]:
    """API 응답 포맷팅"""
    response = {
        'success': success
    }

    if data is not None:
        response['data'] = data

    if message:
        response['message'] = message

    return response