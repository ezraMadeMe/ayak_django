# user/views/medical_info.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from user.models.user_medical_info import UserMedicalInfo
from user.serializers import UserMedicalInfoSerializer


class UserMedicalInfoViewSet(viewsets.ModelViewSet):
    serializer_class = UserMedicalInfoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserMedicalInfo.objects.filter(
            user=self.request.user
        ).select_related('hospital', 'illness')