import random
import string

from django.core.exceptions import ValidationError
from django.db import models

class BaseModel(models.Model):
    """공통 필드를 포함하는 추상 모델"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        abstract = True


class CodeGeneratorMixin:
    """코드 생성을 위한 믹스인"""

    @staticmethod
    def generate_unique_code(model_class, field_name, length=8, max_attempts=10):
        """고유한 코드 생성"""
        characters = string.ascii_uppercase + string.digits

        for _ in range(max_attempts):
            code = ''.join(random.choices(characters, k=length))
            if not model_class.objects.filter(**{field_name: code}).exists():
                return code

        raise ValidationError(f"고유한 {field_name} 생성에 실패했습니다.")
