# user/models.py에 추가할 모델들

from django.db import models

class HospitalCache(models.Model):
    """병원정보 캐시 테이블"""
    # 기본 식별 정보
    hospital_code = models.CharField(max_length=20, unique=True, verbose_name="요양기관기호")
    hospital_name = models.CharField(max_length=200, verbose_name="요양기관명")
    hospital_phone = models.CharField(max_length=20, blank=True, verbose_name="전화번호")

    # 분류 정보
    hospital_type_code = models.CharField(max_length=10, blank=True, verbose_name="종별코드")
    hospital_type_name = models.CharField(max_length=50, blank=True, verbose_name="종별코드명")
    establishment_type_code = models.CharField(max_length=10, blank=True, verbose_name="설립구분코드")
    establishment_type_name = models.CharField(max_length=50, blank=True, verbose_name="설립구분명")

    # 주소 정보
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="우편번호")
    address = models.CharField(max_length=500, blank=True, verbose_name="주소")
    road_address = models.CharField(max_length=500, blank=True, verbose_name="도로명주소")

    # 지역 정보
    sido_code = models.CharField(max_length=10, blank=True, verbose_name="시도코드")
    sido_name = models.CharField(max_length=50, blank=True, verbose_name="시도명")
    sigungu_code = models.CharField(max_length=10, blank=True, verbose_name="시군구코드")
    sigungu_name = models.CharField(max_length=50, blank=True, verbose_name="시군구명")

    # 위치 정보 (선택사항)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="위도")
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True, verbose_name="경도")

    # 운영 정보
    homepage_url = models.URLField(blank=True, verbose_name="홈페이지")
    business_status_code = models.CharField(max_length=10, blank=True, verbose_name="운영상태코드")
    business_status_name = models.CharField(max_length=50, blank=True, verbose_name="운영상태명")

    # 의료진 정보
    total_doctors = models.IntegerField(default=0, verbose_name="총의사수")
    total_beds = models.IntegerField(default=0, verbose_name="총병상수")

    # 진료과목 정보 (JSON 필드로 저장)
    medical_subjects = models.JSONField(default=list, blank=True, verbose_name="진료과목목록")

    # 데이터 관리
    data_reference_date = models.DateField(null=True, blank=True, verbose_name="데이터기준일자")
    is_active = models.BooleanField(default=True, verbose_name="활성화여부")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="최종수정일시")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    class Meta:
        db_table = 'hospital_cache'
        verbose_name = "병원정보캐시"
        verbose_name_plural = "병원정보캐시"
        ordering = ['hospital_name']
        indexes = [
            models.Index(fields=['hospital_code']),
            models.Index(fields=['hospital_name']),
            models.Index(fields=['sido_code', 'sigungu_code']),
            models.Index(fields=['hospital_type_code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.hospital_code} - {self.hospital_name}"


class DiseaseCache(models.Model):
    """질병정보 캐시 테이블"""
    # 기본 식별 정보
    disease_code = models.CharField(max_length=20, unique=True, verbose_name="질병코드")
    disease_name_kr = models.CharField(max_length=500, verbose_name="질병명(한글)")
    disease_name_en = models.CharField(max_length=500, blank=True, verbose_name="질병명(영문)")

    class Meta:
        db_table = 'disease_cache'
        verbose_name = "질병정보캐시"
        verbose_name_plural = "질병정보캐시"
        ordering = ['disease_code']

    def __str__(self):
        return f"{self.disease_code} - {self.disease_name_kr}"