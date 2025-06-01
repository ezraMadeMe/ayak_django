from rest_framework import serializers

from bokyak.models.medication_cycle import MedicationCycle
from bokyak.models.medication_record import MedicationRecord
from bokyak.serializers.serializer import MedicationCycleListSerializer, MedicationAlertSerializer, MedicationRecordSerializer
from user.models import AyakUser, Hospital, Illness, MainIngredient, MedicationIngredient, Medication, UserMedicalInfo


# User 관련 시리얼라이저
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AyakUser
        fields = ['user_id', 'user_name', 'join_date', 'push_agree', 'is_active']
        read_only_fields = ['join_date']


# Hospital 관련 시리얼라이저
class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = [
            'hospital_id', 'hosp_code', 'hosp_name', 'hosp_type',
            'doctor_name', 'address', 'phone_number', 'created_at'
        ]
        read_only_fields = ['hospital_id', 'created_at']

    def create(self, validated_data):
        # user는 현재 로그인한 사용자로 설정
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class HospitalListSerializer(serializers.ModelSerializer):
    """병원 목록용 간단한 시리얼라이저"""

    class Meta:
        model = Hospital
        fields = ['hospital_id', 'hosp_name', 'doctor_name', 'hosp_type']


# Illness 관련 시리얼라이저
class IllnessSerializer(serializers.ModelSerializer):
    ill_type_display = serializers.CharField(source='get_ill_type_display', read_only=True)

    class Meta:
        model = Illness
        fields = [
            'illness_id', 'ill_type', 'ill_type_display', 'ill_name',
            'ill_code', 'ill_start', 'ill_end', 'is_chronic', 'created_at'
        ]
        read_only_fields = ['illness_id', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class IllnessListSerializer(serializers.ModelSerializer):
    """질병 목록용 간단한 시리얼라이저"""
    ill_type_display = serializers.CharField(source='get_ill_type_display', read_only=True)

    class Meta:
        model = Illness
        fields = ['illness_id', 'ill_name', 'ill_type_display', 'is_chronic']


# MainIngredient 관련 시리얼라이저
class MainIngredientSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    full_density_info = serializers.ReadOnlyField()

    class Meta:
        model = MainIngredient
        fields = [
            'ingr_code', 'original_code', 'dosage_form_code', 'dosage_form',
            'main_ingr_name_kr', 'main_ingr_name_en', 'classification_code',
            'administration_route', 'main_ingr_density', 'main_ingr_unit',
            'original_density_text', 'is_combination', 'combination_group',
            'is_active', 'notes', 'data_quality_score', 'display_name', 'full_density_info'
        ]
        read_only_fields = ['ingr_code', 'data_quality_score', 'display_name', 'full_density_info']

# MedicationIngredient 관련 시리얼라이저
class MedicationIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.display_name', read_only=True)

    class Meta:
        model = MedicationIngredient
        fields = [
            'ingredient', 'ingredient_name', 'content_amount',
            'content_unit', 'is_active_ingredient'
        ]


# Medication 관련 시리얼라이저
class MedicationSerializer(serializers.ModelSerializer):
    ingredient_details = MedicationIngredientSerializer(many=True, read_only=True)
    main_ingredient_names = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = [
            'item_seq', 'item_name', 'entp_name', 'item_image',
            'class_name', 'dosage_form', 'is_prescription',
            'ingredient_details', 'main_ingredient_names'
        ]

    def get_main_ingredient_names(self, obj):
        return [
            ingredient.ingredient.display_name
            for ingredient in obj.ingredient_details.filter(is_active_ingredient=True)
        ]


class MedicationListSerializer(serializers.ModelSerializer):
    """약물 목록용 간단한 시리얼라이저"""
    main_ingredient = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = ['item_seq', 'item_name', 'entp_name', 'class_name', 'main_ingredient']

    def get_main_ingredient(self, obj):
        main_ingredient = obj.ingredient_details.filter(is_active_ingredient=True).first()
        if main_ingredient:
            return {
                'name': main_ingredient.ingredient.display_name,
                'amount': f"{main_ingredient.content_amount}{main_ingredient.content_unit}"
            }
        return None


# UserMedicalInfo 관련 시리얼라이저
class UserMedicalInfoSerializer(serializers.ModelSerializer):
    hospital_name = serializers.CharField(source='hospital.hosp_name', read_only=True)
    illness_name = serializers.CharField(source='illness.ill_name', read_only=True)
    doctor_name = serializers.CharField(source='hospital.doctor_name', read_only=True)

    class Meta:
        model = UserMedicalInfo
        fields = [
            'id', 'user', 'hospital', 'illness', 'is_primary',
            'hospital_name', 'illness_name', 'doctor_name'
        ]

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

# 홈화면용 종합 시리얼라이저
class HomeInfoSerializer(serializers.Serializer):
    """홈화면에서 사용할 종합 정보 시리얼라이저"""
    recent_cycles = MedicationCycleListSerializer(many=True, read_only=True)
    active_alerts = MedicationAlertSerializer(many=True, read_only=True)
    recent_records = MedicationRecordSerializer(many=True, read_only=True)
    upcoming_visits = serializers.SerializerMethodField()

    def get_upcoming_visits(self, obj):
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        upcoming = MedicationCycle.objects.filter(
            group__medical_info__user=obj,
            next_visit_date__gte=today,
            next_visit_date__lte=today + timedelta(days=30)
        ).order_by('next_visit_date')

        return [{
            'id': cycle.id,
            'group_name': cycle.group.group_name,
            'hospital_name': cycle.group.medical_info.hospital.hosp_name,
            'visit_date': cycle.next_visit_date,
            'days_remaining': (cycle.next_visit_date - today).days
        } for cycle in upcoming]


# 복약 분석용 시리얼라이저
class MedicationAnalysisSerializer(serializers.Serializer):
    """복약 분석 화면용 시리얼라이저"""
    medication_trends = serializers.SerializerMethodField()
    prn_usage_stats = serializers.SerializerMethodField()
    cycle_changes = serializers.SerializerMethodField()

    def get_medication_trends(self, obj):
        # 약물별 용량 변화 추이 데이터
        cycles = MedicationCycle.objects.filter(
            group__medical_info__user=obj
        ).prefetch_related('medication_details__medication').order_by('cycle_start')

        trends = {}
        for cycle in cycles:
            for detail in cycle.medication_details.all():
                med_name = detail.medication.item_name
                if med_name not in trends:
                    trends[med_name] = []

                daily_dose = float(detail.quantity_per_dose) * detail.frequency_per_interval
                trends[med_name].append({
                    'cycle_number': cycle.cycle_number,
                    'date': cycle.cycle_start.strftime('%m월%d일'),
                    'daily_dose': daily_dose,
                    'medication_category': detail.medication.class_name or '기타'
                })

        return trends

    def get_prn_usage_stats(self, obj):
        # PRN 사용 통계 (필요시 복용 기록)
        prn_records = MedicationRecord.objects.filter(
            cycle__group__medical_info__user=obj,
            medication_detail__dosage_interval='PRN'
        ).order_by('-record_date')

        return [{
            'date': record.record_date,
            'medication_name': record.medication_detail.medication.item_name,
            'quantity': float(record.quantity_taken),
            'reason': record.notes or record.symptoms,
            'category': self._categorize_prn_reason(record.notes or record.symptoms)
        } for record in prn_records]

    def get_cycle_changes(self, obj):
        # 사이클별 변화 분석
        cycles = MedicationCycle.objects.filter(
            group__medical_info__user=obj
        ).order_by('cycle_start')

        changes = []
        prev_medications = set()

        for cycle in cycles:
            current_medications = set()
            for detail in cycle.medication_details.all():
                med_info = (
                    detail.medication.item_name,
                    float(detail.quantity_per_dose) * detail.frequency_per_interval
                )
                current_medications.add(med_info)

            if prev_medications:
                added = current_medications - prev_medications
                discontinued = prev_medications - current_medications

                changes.append({
                    'cycle_number': cycle.cycle_number,
                    'date': cycle.cycle_start.strftime('%m월%d일'),
                    'reason': cycle.notes,
                    'added': [med[0] for med in added],
                    'discontinued': [med[0] for med in discontinued],
                    'total_changes': len(added) + len(discontinued)
                })

            prev_medications = current_medications

        return changes

    def _categorize_prn_reason(self, reason):
        """PRN 사용 사유 카테고리화"""
        if not reason:
            return 'other'

        reason_lower = reason.lower()
        if any(word in reason_lower for word in ['불안', 'anxiety']):
            return 'anxiety'
        elif any(word in reason_lower for word in ['패닉', 'panic']):
            return 'panic'
        elif any(word in reason_lower for word in ['수면', '잠', 'sleep']):
            return 'sleep'
        elif any(word in reason_lower for word in ['스트레스', 'stress']):
            return 'stress'
        elif any(word in reason_lower for word in ['공포', 'phobia']):
            return 'phobia'
        elif any(word in reason_lower for word in ['강박', 'obsessive']):
            return 'obsessive'
        else:
            return 'other'

# 검색용 시리얼라이저
class MedicationSearchSerializer(serializers.ModelSerializer):
    """약물 검색용 시리얼라이저"""
    main_ingredients = serializers.SerializerMethodField()

    class Meta:
        model = Medication
        fields = ['item_seq', 'item_name', 'entp_name', 'class_name', 'main_ingredients']

    def get_main_ingredients(self, obj):
        ingredients = obj.ingredient_details.filter(is_active_ingredient=True)
        return [
            {
                'name': ing.ingredient.display_name,
                'amount': f"{ing.content_amount}{ing.content_unit}"
            }
            for ing in ingredients[:2]  # 주요 성분 2개만 표시
        ]