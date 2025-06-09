from datetime import datetime, timedelta

from celery.bin.control import status
from rest_framework.decorators import permission_classes, api_view
from rest_framework.response import Response
from rest_framework_api_key.models import APIKey
from rest_framework.permissions import IsAuthenticated

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def apikey(request):
    username = request.user.username
    if request.method == 'GET':
        response = {}
        keys = APIKey.objects.all()
        for key in keys:
            if key.name == username:
                response['apikey'] = key.prefix + '*****'
                response['created'] = key.created
                response['expires'] = key.expiry_date
                break
        return Response(response, status=status.HTTP_200_OK)
    else:
        keys = APIKey.objects.all()
        for key in keys:
            if key.name == username:
                key.delete()
                break
        api_key, key = APIKey.objects.create_key(name=request.user.username)
        expires = datetime.now() + timedelta(days=90)
        api_key.expiry_date = expires
        api_key.save()
        return Response({'apikey': key, 'expires': expires}, status=status.HTTP_200_OK)