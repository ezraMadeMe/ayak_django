from django.db import models


class BokyakGroup(models.Model):
    class Meta:
        db_table = 'bokyak_group'

    user_id = models.CharField(null=False)          # 유저 아이디
    group_id = models.CharField(primary_key=True, max_length=10, null=False)    # 복약 그룹 코드
    group_name = models.CharField(max_length=20, null=False)                    # 복약 그룹 이름
    rel_hosp = models.CharField(null=True)                                      # 최초 처방 병원 코드
    rel_ill = models.CharField(null=True)           # 관련 질병 코드
    reg_date = models.DateTimeField(null=False)     # 등록일
    mod_date = models.DateTimeField(null=False)     # 수정일


class BokyakCycle(models.Model):
    class Meta:
        db_table = 'bokyak_cycle'

    group_id = models.CharField(null=False)         # 복약 그룹 코드
    cycle_id = models.IntegerField(primary_key=True, null=False)   # 해당 주기 코드
    rel_hosp = models.CharField(null=True)          # 관련 병원 코드
    cycle_start = models.DateTimeField(null=False)  # 주기 시작일(최근 처방일)
    cycle_end = models.DateTimeField(null=True)     # 주기 종료일(다음 방문일)


class Bokyak(models.Model):
    class Meta:
        db_table = 'bokyak_detail'

    group_id = models.CharField()                       # 복약 그룹 코드
    cycle_id = models.IntegerField()                    # 주기 코드
    rel_ill = models.CharField(null=True)               # 관련 질병 코드
    item_seq = models.IntegerField(null=False)          # 의약품 일련번호
    med_term = models.CharField(null=True)              # D : 일 / W : 주 / P : prn
    per_term = models.IntegerField(null=False)          # 주기당 복약 횟수
    per_num = models.IntegerField(default=0)           # 회당 복약 개수
    med_total = models.IntegerField(null=False)         # 총 처방일수


class BokyakRecord(models.Model):
    class Meta:
        db_table = 'bokyak_record'

    group_id = models.CharField()                   # 복약 그룹 코드
    cycle_id = models.IntegerField(default='10000000')                    # 복약 주기 코드
    record_id = models.IntegerField(primary_key=True, default='10000000') # 기록 고유 번호
    rel_ill = models.CharField(null=True)           # 관련 질병 코드
    rel_item = models.CharField(null=False)         # 관련 의약품 코드
    rec_date = models.DateTimeField(null=False)     # 기록일
    reg_date = models.DateTimeField(null=False)     # 등록일
    record = models.CharField(null=False)           # 기록 내용