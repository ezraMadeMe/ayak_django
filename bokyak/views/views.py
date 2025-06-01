from rest_framework.decorators import api_view


# 복약 세부 정보
@api_view(['GET', 'POST', 'DELETE'])
def bokyak_detail(request):
    # 복약 세부 정보 조회
    if request.method == "GET":
        return None

    # 복약 세부 정보 등록/수정
    if request.method == "POST":
        return None

    # 복약 세부 정보 삭제
    if request.method == "DELETE":
        return None
    return None

# 복약 그룹
@api_view(['GET', 'POST', 'DELETE'])
def bokyak_group(request, user_id):
    # 복약 그룹 조회
    if request.method == "GET":
        return None

    # 복약 그룹 등록/수정
    if request.method == "POST":
        return None

    # 복약 그룹 삭제
    if request.method == "DELETE":
        return None
    return None

# 복약 주기
@api_view(['GET', 'POST', 'DELETE'])
def bokyak_cycle(request):
    # 복약 주기 조회
    if request.method == "GET":
        return None

    # 복약 주기 등록/수정
    if request.method == "POST":
        return None

    # 복약 주기 삭제
    if request.method == "DELETE":
        return None
    return None

# 복약 기록 정보
@api_view(['GET', 'POST', 'DELETE'])
def bokyak_record(request):
    # 복약 기록 정보 조회
    if request.method == "GET":
        return None

   # 복약 기록 정보 등록/수정
    if request.method == "POST":
        return None

    # 복약 기록 삭제
    if request.method == "DELETE":
        return None
    return None
