import random
import string

from django.db import models
from pydantic import ValidationError
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.response import Response


class ValidatedModel(models.Model):
    class Meta:
        abstract = True

    def clean(self):

        return

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def add_unique_constraint(cls, fields, message):
        """
        :param fields: 유니크 제약조건 대상 필드 리스트
        :param message: 중복 시 보여줄 메시지
        """
        def _clean(self):
            filter_kwargs = {field: getattr(self, field) for field in fields}
            # 중복 검사
            qs = self.__class__.objects.filter(**filter_kwargs)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(message)

        cls.clean = _clean
        return Response({'message':'정상적으로 입력되었습니다.'}, status=status.HTTP_200_OK)

class User(ValidatedModel):
    class Meta:
        db_table = 'user'

    user_id = models.CharField(primary_key=True, max_length=10, null=False) # 유저 아이디
    user_name = models.CharField(max_length=20, null=False) # 유저 이름
    join_date = models.DateTimeField(null=False)            # 가입일
    push_agree = models.BooleanField(null=False)            # 푸시 동의 여부

class Hospital(ValidatedModel):
    class Meta:
        db_table = 'hospital'
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'hosp_id', 'hosp_name'],
                name='unique_user_hosp'
            )
        ]

    user_id = models.CharField()                                # 유저 아이디
    hosp_id = models.CharField(default="")                      # 병원 코드(telno)
    hosp_name = models.CharField(default="")                    # 병원 이름(yadmNm)
    hosp_type = models.CharField(default="")                    # 병원 종별코드(clCdNm)
    doctor_name = models.CharField(max_length=30, default="")   # 의사명

class Illness(ValidatedModel):
    class Meta:
        db_table = 'illness'
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'ill_id', 'ill_name'],
                name='unique_user_ill'
            )
        ]

    class IllCode(models.TextChoices):
        DISEASE = 'D', '질병'
        SYMPTOM = 'S', '증상'

    user_id = models.CharField()                            # 유저 아이디
    ill_type = models.CharField(max_length=1, choices=IllCode.choices, default=IllCode.DISEASE)# D : 질병 / S : 증상
    ill_id = models.CharField(max_length=8, blank=True)    # 질병/증상 코드
    ill_name = models.CharField(max_length=50, null=False) # 질병/증상 이름
    ill_start = models.DateField(null=True)                 # 발병일/발생일
    ill_end = models.DateField(blank=True, null=True)       # 완치 여부

    # 증상 : 8자리 영대문자+숫자코드 생성 / 질병 : 질병코드
    def save(self, *args, **kwargs):
        value = self.ill_id
        if not value or value.strip() == "":
            while True:
                new_value = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not Illness.objects.filter(ill_id=new_value).exists():
                    break
            self.ill_id = new_value
        else:
            if len(value) in [3, 4, 5]:
                pass

        super().save(*args, **kwargs)

# 주성분
class MainIngredient(ValidatedModel):
    class Meta:
        db_table = 'main_ingredient'

    ingr_code = models.CharField(max_length=9)                    # 일반명 코드
    main_ingr_item = models.CharField(max_length=100, null=False) # 주성분명(영문)
    main_ingr_den = models.FloatField(null=False)                 # 주성분 함량
    main_ingr_unit = models.CharField(null=False)                 # 주성분 함량 단위

# 의약품
class Medication(ValidatedModel):
    class Meta:
        db_table = 'medication'

    item_seq = models.IntegerField(primary_key=True)                # 의약품 코드
    item_name = models.CharField(max_length=100, null=False)        # 의약품명
    main_item_ingr = models.CharField(null=False)                   # 주성분명(국문)
    main_ingr_eng = models.CharField(null=False)                    # 주성분명(영문)
    entp_name = models.CharField()                                  # 업체명
    item_image = models.ImageField()                                # 의약품 이미지

# 사용자 연관 병원+질병 정보
class UserInfo(ValidatedModel):
    class Meta:
        db_table = 'user_info'
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'info_name'],
                name='unique_user_info_name'
            ),
            models.UniqueConstraint(
                fields=['info_name', 'hosp_info', 'ill_info'],
                name='unique_user_info'
            )
        ]

    user_id = models.ForeignKey(User, on_delete=models.CASCADE, to_field='user_id')
    info_name = models.CharField(null=False) # 요약 정보 이름
    hosp_info = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='user_info', unique=True)
    ill_info = models.ForeignKey(Illness, on_delete=models.CASCADE, related_name='user_info')

UserInfo.add_unique_constraint(['user_id', 'info_name'],"중복된 이릅입니다.")
UserInfo.add_unique_constraint(['info_name', 'hosp_info', 'ill_info'],"이미 등록된 정보입니다.")

class MedInfo(ValidatedModel):
    class Meta:
        db_table = 'med_info'
        constraints = [
            models.UniqueConstraint(
                fields=['user_id', 'info_name'],
                name='unique_med_info_name'
            ),
            models.UniqueConstraint(
                fields=['info_name', 'ill_info', 'medi_info'],
                name='unique_med_info'
            )
        ]

    user_id = models.ForeignKey(User, on_delete=models.CASCADE, to_field='user_id')
    info_name = models.CharField(null=False)  # 요약 정보 이름
    ill_info = models.ForeignKey(Illness, on_delete=models.CASCADE, related_name='med_info')
    medi_info = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='med_info')

MedInfo.add_unique_constraint(['user_id', 'info_name'],"중복된 이름입니다.")
MedInfo.add_unique_constraint(['info_name', 'ill_info', 'medi_info'],"이미 등록된 정보입니다.")