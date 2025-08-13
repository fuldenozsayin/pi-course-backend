#Backend’de select_related / prefetch_related ile N+1 önleme. 
from django.contrib.auth import get_user_model
from rest_framework import views, permissions, response, status
from core.serializers import MeSerializer, MeUpdateSerializer
from core.models import Subject

User = get_user_model()

class MeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # tutorprofile + subjects için prefetch
        user = (User.objects
                .filter(id=request.user.id)
                .select_related("tutorprofile", "studentprofile")
                .prefetch_related("tutorprofile__subjects")
                .get())
        data = MeSerializer(user).data
        return response.Response(data)

    def patch(self, request):
        ser = MeUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.update(request.user, ser.validated_data)
        # güncel veri döndür
        user = (User.objects
                .filter(id=request.user.id)
                .select_related("tutorprofile", "studentprofile")
                .prefetch_related("tutorprofile__subjects")
                .get())
        return response.Response(MeSerializer(user).data, status=status.HTTP_200_OK)
