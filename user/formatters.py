from typing import Dict, Any
from bokyak.formatters import format_prescription


def format_ayak_user(user) -> Dict[str, Any]:
    """사용자 정보 포맷팅"""
    return {
        'user_id': user.user_id,
        'user_name': user.user_name,
        'join_date': user.join_date.isoformat() if user.join_date else None,
        'push_agree': user.push_agree,
        'is_active': user.is_active,
        'social_provider': user.social_provider,
        'social_id': user.social_id,
        'email': user.email,
        'profile_image_url': user.profile_image_url,
        'phone_number': user.phone_number,
        'birth_date': user.birth_date.isoformat() if user.birth_date else None,
        'gender': user.gender,
        'notification_enabled': user.notification_enabled,
        'marketing_agree': user.marketing_agree,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        'last_login_date': user.last_login_date.isoformat() if user.last_login_date else None,
    }


def format_hospital_cache(hospital_cache) -> Dict[str, Any]:
    """병원 캐시 정보 포맷팅"""
    return {
        'hospital_code': hospital_cache.hospital_code,
        'hospital_name': hospital_cache.hospital_name,
        'hospital_phone': hospital_cache.hospital_phone,
        'hospital_type_code': hospital_cache.hospital_type_code,
        'hospital_type_name': hospital_cache.hospital_type_name,
        'establishment_type_code': hospital_cache.establishment_type_code,
        'establishment_type_name': hospital_cache.establishment_type_name,
        'postal_code': hospital_cache.postal_code,
        'address': hospital_cache.address,
        'road_address': hospital_cache.road_address,
        'sido_code': hospital_cache.sido_code,
        'sido_name': hospital_cache.sido_name,
        'sigungu_code': hospital_cache.sigungu_code,
        'sigungu_name': hospital_cache.sigungu_name,
        'latitude': float(hospital_cache.latitude) if hospital_cache.latitude else None,
        'longitude': float(hospital_cache.longitude) if hospital_cache.longitude else None,
        'homepage_url': hospital_cache.homepage_url,
        'business_status_code': hospital_cache.business_status_code,
        'business_status_name': hospital_cache.business_status_name,
        'total_doctors': hospital_cache.total_doctors,
        'total_beds': hospital_cache.total_beds,
        'medical_subjects': hospital_cache.medical_subjects,
        'data_reference_date': hospital_cache.data_reference_date.isoformat() if hospital_cache.data_reference_date else None,
        'is_active': hospital_cache.is_active,
        'last_updated': hospital_cache.last_updated.isoformat() if hospital_cache.last_updated else None,
        'created_at': hospital_cache.created_at.isoformat() if hospital_cache.created_at else None,
    }


def format_disease_cache(disease_cache) -> Dict[str, Any]:
    """질병 캐시 정보 포맷팅"""
    return {
        'disease_code': disease_cache.disease_code,
        'disease_name_kr': disease_cache.disease_name_kr,
        'disease_name_en': disease_cache.disease_name_en,
    }


def format_hospital(hospital) -> Dict[str, Any]:
    """병원 정보 포맷팅"""
    return {
        'hospital_id': hospital.hospital_id,
        'user': format_ayak_user(hospital.user) if hospital.user else None,
        'hosp_code': hospital.hosp_code,
        'hosp_name': hospital.hosp_name,
        'hosp_type': hospital.hosp_type,
        'doctor_name': hospital.doctor_name,
        'address': hospital.address,
        'phone_number': hospital.phone_number,
        'created_at': hospital.created_at.isoformat() if hospital.created_at else None,
        'updated_at': hospital.updated_at.isoformat() if hospital.updated_at else None,
    }


def format_illness(illness) -> Dict[str, Any]:
    """질병/증상 정보 포맷팅"""
    return {
        'illness_id': illness.illness_id,
        'user': format_ayak_user(illness.user) if illness.user else None,
        'ill_type': illness.ill_type,
        'ill_name': illness.ill_name,
        'ill_code': illness.ill_code,
        'ill_start': illness.ill_start.isoformat() if illness.ill_start else None,
        'ill_end': illness.ill_end.isoformat() if illness.ill_end else None,
        'is_chronic': illness.is_chronic,
        'created_at': illness.created_at.isoformat() if illness.created_at else None,
        'updated_at': illness.updated_at.isoformat() if illness.updated_at else None,
    }


def format_main_ingredient(ingredient) -> Dict[str, Any]:
    """주성분 정보 포맷팅"""
    return {
        'ingr_code': ingredient.ingr_code,
        'original_code': ingredient.original_code,
        'dosage_form_code': ingredient.dosage_form_code,
        'dosage_form': ingredient.dosage_form,
        'main_ingr_name_kr': ingredient.main_ingr_name_kr,
        'main_ingr_name_en': ingredient.main_ingr_name_en,
        'classification': ingredient.classification,
        'route': ingredient.route,
        'main_ingr_density': float(ingredient.main_ingr_density) if ingredient.main_ingr_density else None,
        'main_ingr_unit': ingredient.main_ingr_unit,
        'original_density_notation': ingredient.original_density_notation,
        'is_combination_drug': ingredient.is_combination_drug,
        'combination_group': ingredient.combination_group,
        'is_active': ingredient.is_active,
        'notes': ingredient.notes,
        'data_quality_score': ingredient.data_quality_score,
        'created_at': ingredient.created_at.isoformat() if ingredient.created_at else None,
        'updated_at': ingredient.updated_at.isoformat() if ingredient.updated_at else None,
    }


def format_medication(medication) -> Dict[str, Any]:
    """의약품 정보 포맷팅"""
    return {
        'medication_id': medication.medication_id,
        'medication_name': medication.medication_name,
        'main_item_ingr': medication.main_item_ingr,
        'main_ingr_eng': medication.main_ingr_eng,
        'ingredient': format_main_ingredient(medication.ingredient) if medication.ingredient else None,
        'manufacturer': medication.manufacturer,
        'item_image': medication.item_image.url if medication.item_image else None,
        'created_at': medication.created_at.isoformat() if medication.created_at else None,
        'updated_at': medication.updated_at.isoformat() if medication.updated_at else None,
    }


def format_medication_ingredient(med_ingredient) -> Dict[str, Any]:
    """의약품-주성분 연결 정보 포맷팅"""
    return {
        'id': med_ingredient.id,
        'medication': format_medication(med_ingredient.medication) if med_ingredient.medication else None,
        'ingredient': format_main_ingredient(med_ingredient.ingredient) if med_ingredient.ingredient else None,
        'amount': float(med_ingredient.amount) if med_ingredient.amount else None,
        'unit': med_ingredient.unit,
        'is_main': med_ingredient.is_main,
        'created_at': med_ingredient.created_at.isoformat() if med_ingredient.created_at else None,
        'updated_at': med_ingredient.updated_at.isoformat() if med_ingredient.updated_at else None,
    }


def format_user_medical_info(medical_info) -> Dict[str, Any]:
    """사용자 의료 정보 포맷팅"""
    # 순환 참조를 피하기 위해 필요한 경우에만 동적으로 import
    return {
        'id': medical_info.id,
        'user': format_ayak_user(medical_info.user) if medical_info.user else None,
        'hospital': format_hospital(medical_info.hospital) if medical_info.hospital else None,
        'illness': format_illness(medical_info.illness) if medical_info.illness else None,
        'prescription': {
            'prescription_id': medical_info.prescription.prescription_id,
            'prescription_date': medical_info.prescription.prescription_date.isoformat() if medical_info.prescription and medical_info.prescription.prescription_date else None,
            'is_active': medical_info.prescription.is_active if medical_info.prescription else None,
        } if medical_info.prescription else None,
        'created_at': medical_info.created_at.isoformat() if medical_info.created_at else None,
        'updated_at': medical_info.updated_at.isoformat() if medical_info.updated_at else None,
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