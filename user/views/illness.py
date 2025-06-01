# user/views/illness.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from user.models.illness import Illness
from user.serializers import IllnessSerializer


class IllnessViewSet(viewsets.ModelViewSet):
    serializer_class = IllnessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Illness.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def chronic_illnesses(self, request):
        """만성 질환 목록"""
        chronic_illnesses = self.get_queryset().filter(is_chronic=True)
        serializer = self.get_serializer(chronic_illnesses, many=True)
        return Response(serializer.data)