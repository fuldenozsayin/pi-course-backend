# core/views/lesson_requests.py
#Backend’de select_related / prefetch_related ile N+1 önleme. 
from rest_framework import viewsets, mixins, permissions
from core.models import LessonRequest
from core.serializers import LessonRequestSerializer

class LessonRequestViewSet(mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Listeleme: N+1'ı kır.
        """
        base = LessonRequest.objects.for_list()  # select_related zinciri
        user = self.request.user

        # Öğrenci ise sadece kendi talepleri; eğitmen ise kendisine gelenler
        if hasattr(user, "student_profile"):
            return base.filter(student__user=user).order_by("-created_at")
        if hasattr(user, "tutor_profile"):
            return base.filter(tutor__user=user).order_by("-created_at")
        # Admin veya özel roller:
        return base.order_by("-created_at")
