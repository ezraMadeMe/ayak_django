import random
import string

from django.db import models
from django.db.models import UniqueConstraint, Max
from pydantic import ValidationError

from user.models import UserInfo, MedInfo, ValidatedModel


class BokyakGroup(ValidatedModel):
    class Meta:
        db_table = 'bokyak_group'

    group_info = models.ManyToManyField(UserInfo, related_name='bokyak_group')     # 사용자 정보
    group_id = models.CharField(primary_key=True, max_length=8, editable=False, unique=True)    # 복약 그룹 코드
    group_name = models.CharField(max_length=20, null=False) # 복약 그룹 이름
    reg_date = models.DateTimeField(null=False)     # 등록일
    mod_date = models.DateTimeField(null=False)     # 수정일

    # 8자리 영대문자+숫자코드 생성
    def save(self, *args, **kwargs):
        if not self.group_id:
            characters = string.ascii_uppercase + string.digits
            for _ in range(10):  # 반복 시도
                new_code = ''.join(random.choices(characters, k=8))
                if not BokyakGroup.objects.filter(group_id=new_code).exists():
                    self.group_id = new_code
                    break
            else:
                raise ValidationError("중복된 코드 생성 실패")
        super().save(*args, **kwargs)


class BokyakCycle(ValidatedModel):
    class Meta:
        db_table = 'bokyak_cycle'
        constraints = [
            UniqueConstraint(
                fields=['group_id', 'cycle_id'],
                name='unique_user_group_cycle'
            )
        ]

    group_id = models.ForeignKey(BokyakGroup,on_delete=models.CASCADE, to_field='group_id')         # 복약 그룹 코드
    cycle_id = models.IntegerField(blank=True, null=True, default=10000)   # 해당 주기 코드
    rel_hosp = models.ForeignKey(UserInfo, on_delete=models.CASCADE, to_field='hosp_info')          # 관련 병원 코드
    cycle_start = models.DateTimeField(null=False)  # 주기 시작일(최근 처방일)
    cycle_end = models.DateTimeField(null=True)     # 주기 종료일(다음 방문일)

    # 복약그룹별 복약주기 AI
    def save(self, *args, **kwargs):
        if self.cycle_id is None:
            max_cycle = BokyakCycle.objects.filter(group_id=self.group_id).aggregate(
                Max('cycle_id')
            )['cycle_id__max']
            self.cycle_id = (max_cycle or 0) + 1
        super().save(*args, **kwargs)

class Bokyak(ValidatedModel):
    class Meta:
        db_table = 'bokyak_detail'

    class MedTerm(models.TextChoices):
        HOUR = 'H', '시간'
        DAY = 'D', '하루'
        WEEK = 'W', '한주'
        PRN = 'P', '필요시'

    rel_cycle = models.ForeignKey(BokyakCycle, on_delete=models.CASCADE, related_name='bokyak')
    rel_med = models.ForeignKey(MedInfo, on_delete=models.CASCADE, related_name='bokyak')
    med_term = models.CharField(max_length=1,choices=MedTerm.choices,default=MedTerm.DAY) # H : 시간 / D : 일 / W : 주 / P : prn
    per_term = models.IntegerField(default=1)          # 주기당 복약 횟수
    per_num = models.IntegerField(default=1)           # 회당 복약 개수
    med_total = models.IntegerField(default=1)         # 총 처방일수


class BokyakRecord(ValidatedModel):
    class Meta:
        db_table = 'bokyak_record'

    rel_cycle = models.ForeignKey(BokyakCycle, on_delete=models.CASCADE, related_name='bokyak_record')
    rel_med = models.ForeignKey(MedInfo, on_delete=models.CASCADE, related_name='bokyak_record')
    rec_date = models.DateTimeField(null=False)     # 기록일
    reg_date = models.DateTimeField(null=False)     # 등록일
    record = models.CharField(null=False)           # 기록 내용