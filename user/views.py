from django.http import HttpResponse
from rest_framework.decorators import api_view
from user.models import User, Illness, Hospital
from user.serializer import UserSerializer, IllnessSerializer


kauth_host = "https://kauth.kakao.com"
kapi_host = "https://kapi.kakao.com"

# 카카오 로그인
@api_view(['GET', 'POST'])
def kakao_login(request):

    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        response = User.objects.get(user_id=user_id)

        return response.data

    if request.method == 'POST':
        user = User(user_id=request.data['user_id'], user_name=request.data['user_name'], join_date=request.data['join_date'], push_agree=request.data['push_agree'])
        res = user.save()

        if res.status_code == 200:
            return HttpResponse(res.json())
        else:
            return HttpResponse(res.status_code)

    return None


# 카카오 로그아웃
@api_view(['POST'])
def kakao_logout(request):
    return None


# 계정 삭제
@api_view(['DELETE'])
def delete_account(request):
    return None


# 병원 정보
@api_view(['GET', 'POST', 'DELETE'])
def hospital_info(request):
    # 등록 병원 정보 조회
    if request.method == "GET":
        user_id = request.GET.get('user_id')
        return None

    # 병원 정보 등록/수정
    if request.method == "POST":
        data = request.data
        register = Hospital(
            user_id=data.get('user_id'),
            hosp_id=data.get('hosp_id'),
            hosp_name=data.get('hosp_name'),
            hosp_type=data.get('hosp_type'),
            doctor_name=data.get('doctor_name')
        )
        response = Hospital.add_unique_constraint(
            ['user_id', 'hosp_id', 'hosp_name'],
            "이미 등록된 병원입니다."
        )
        if response.status_code == 200:
            register.save()
            return response
        else:
            return response.data

    # 병원 정보 삭제
    if request.method == "DELETE":
        return HttpResponse("DELETE")
    return HttpResponse("HOSPITAL_RETURN")


# 질병/증상 정보
@api_view(['GET', 'POST', 'DELETE'])
def illness_info(request):
    # 등록 질병/증상 정보 조회
    if request.method == "GET":
        user_id = request.GET.get('user_id')
        query = list(Illness.objects.filter(user_id=user_id).values())
        serializer = IllnessSerializer(query, many=True)

        return HttpResponse(serializer)

    # 질병/증상 정보 등록/수정
    if request.method == "POST":
        data = request.data
        register = Illness(
            user_id=data.get('user_id'),
            ill_type=data.get('ill_type'),
            ill_id=data.get('ill_id'),
            ill_name=data.get('ill_name'),
            ill_start=data.get('ill_start'),
            ill_end=data.get('ill_end')
        )
        response = Illness.add_unique_constraint(
            ['user_id', 'ill_id', 'ill_name'],
            "이미 등록된 질병/증상입니다."
        )
        if response.status_code == 200:
            register.save()
            return response
        else:
            return response.data

    # 질병/증상 정보 삭제
    if request.method == "DELETE":
        return HttpResponse("DELETE")
    return HttpResponse("ILLNESS_RETURN")
