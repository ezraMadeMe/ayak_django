from django.db import models


class User(models.Model):
    class Meta:
        db_table = 'user'

    user_id = models.CharField(primary_key=True, max_length=10, null=False) # 유저 아이디
    user_name = models.CharField(max_length=20, null=False) # 유저 이름
    join_date = models.DateTimeField(null=False)            # 가입일
    push_agree = models.BooleanField(null=False)            # 푸시 동의 여부


class Hospital(models.Model):
    class Meta:
        db_table = 'hospital'

    user_id = models.CharField()                                # 유저 아이디
    hosp_name = models.CharField(max_length=100, null=False)    # 병원 이름
    hosp_id = models.CharField(null=False, max_length=10)       # 병원 코드(전화번호)
    doctor_name = models.CharField(max_length=100, null=True)   # 의사명


class Illness(models.Model):
    class Meta:
        db_table = 'illness'

    user_id = models.CharField()                            # 유저 아이디
    ill_type = models.CharField(max_length=1, null=False)   # D : 질병 / S : 증상
    ill_id = models.CharField(max_length=10, null=False)    # 질병/증상 코드
    ill_name = models.CharField(max_length=100, null=False) # 질병/증상 이름
    ill_start = models.DateField(null=True)                 # 발병일/발생일
    ill_end = models.BooleanField(default=False)            # 완치 여부

# 주성분
class MainIngredient(models.Model):
    class Meta:
        db_table = 'main_ingredient'

    ingr_code = models.CharField(max_length=9)                    # 일반명 코드
    main_ingr_item = models.CharField(max_length=100, null=False) # 주성분명(영문)
    main_ingr_den = models.FloatField(null=False)                 # 주성분 함량
    main_ingr_unit = models.CharField(null=False)                 # 주성분 함량 단위

# 의약품
class Medication(models.Model):
    class Meta:
        db_table = 'medication'

    item_seq = models.IntegerField(primary_key=True)                # 의약품 코드
    item_name = models.CharField(max_length=100, null=False)        # 의약품명
    main_item_ingr = models.CharField(null=False)                   # 주성분명(국문)
    main_ingr_eng = models.CharField(null=False)                    # 주성분명(영문)
    entp_name = models.CharField()                                  # 업체명
    item_image = models.ImageField()                                # 의약품 이미지
