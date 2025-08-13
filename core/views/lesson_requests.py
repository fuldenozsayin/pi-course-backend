# core/views/lesson_requests.py
#Backend’de select_related / prefetch_related ile N+1 önleme. 
from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins, permissions
from rest_framework.exceptions import PermissionDenied

from core.models import LessonRequest
from core.serializers import (
    LessonRequestCreateSerializer,
    LessonRequestListSerializer,
    LessonRequestStatusSerializer,
)

User = get_user_model()

class IsAuthenticatedJWT(permissions.IsAuthenticated):
    pass


class LessonRequestViewSet(mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    """
    GET /api/lesson-requests?role=student|tutor&status=pending|approved|rejected
    POST /api/lesson-requests
    PATCH /api/lesson-requests/{id}  -> sadece ilgili tutor status güncelleyebilir
    """
    permission_classes = [IsAuthenticatedJWT]
    lookup_field = "id"

    def get_queryset(self):
        qs = (LessonRequest.objects
              .select_related("student", "tutor", "subject"))

        user = self.request.user
        role = self.request.query_params.get("role")

        # Oturum sahibine göre görünüm
        if role == "student" or user.role == "student":
            qs = qs.filter(student=user)
        elif role == "tutor" or user.role == "tutor":
            qs = qs.filter(tutor=user)
        else:
            # admin değilse kendi kayıtlarını görsün
            qs = qs.filter(student=user) | qs.filter(tutor=user)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return LessonRequestCreateSerializer
        if self.action in ("partial_update", "update"):
            return LessonRequestStatusSerializer
        return LessonRequestListSerializer

    def perform_update(self, serializer):
        # sadece ilgili 'tutor' statü güncellesin
        instance = self.get_object()
        if self.request.user != instance.tutor:
            raise PermissionDenied("Only the related tutor can update the status.")
        serializer.save()
