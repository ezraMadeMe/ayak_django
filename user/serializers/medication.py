# user/serializers/medication.py
from rest_framework import serializers
from user.models.medication import MainIngredient, Medication
from user.models.medication_ingredient import MedicationIngredient


class MainIngredientSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    full_density_info = serializers.CharField(read_only=True)

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


class MedicationIngredientSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.display_name', read_only=True)

    class Meta:
        model = MedicationIngredient
        fields = [
            'ingredient', 'ingredient_name', 'content_amount',
            'content_unit', 'is_active_ingredient'
        ]


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