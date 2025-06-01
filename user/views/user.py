# user/views/user.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from user.models.ayakuser import AyakUser
from user.serializers import UserSerializer, UserMedicalInfoSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = AyakUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AyakUser.objects.filter(user_id=self.request.user.user_id)

    @action(detail=True, methods=['get'])
    def medical_summary(self, request, pk=None):
        """사용자의 의료 정보 요약"""
        user = self.get_object()
        medical_info = user.medical_info.select_related('hospital', 'illness').all()

        data = {
            'user': UserSerializer(user).data,
            'medical_info_count': medical_info.count(),
            'medical_info': UserMedicalInfoSerializer(medical_info, many=True).data,
            'active_prescriptions': medical_info.filter(
                prescriptions__is_active=True
            ).count()
        }
        return Response(data)