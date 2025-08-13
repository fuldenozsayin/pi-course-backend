# core/views/tutors.py
#Backend’de select_related / prefetch_related ile N+1 önleme. 
from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import viewsets, mixins, permissions

from core.serializers import TutorMiniSerializer, TutorDetailSerializer

User = get_user_model()

class TutorViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    """
    /api/tutors?subject=<id>&ordering=-rating&search=<q>
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = TutorMiniSerializer
    lookup_field = "id"

    def get_queryset(self):
        qs = (User.objects
              .filter(role="tutor")
              .select_related("tutorprofile")
              .prefetch_related("tutorprofile__subjects"))

        # filtreler
        subject_id = self.request.query_params.get("subject")
        if subject_id:
            qs = qs.filter(tutorprofile__subjects__id=subject_id)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(tutorprofile__bio__icontains=search)
            )

        ordering = self.request.query_params.get("ordering") or "-tutorprofile__rating"
        # güvenli alanlar
        safe_order_map = {
            "rating": "tutorprofile__rating",
            "-rating": "-tutorprofile__rating",
            "hourly_rate": "tutorprofile__hourly_rate",
            "-hourly_rate": "-tutorprofile__hourly_rate",
            "id": "id", "-id": "-id",
        }
        ordering = safe_order_map.get(ordering, "-tutorprofile__rating")
        return qs.order_by(ordering).distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TutorDetailSerializer
        return TutorMiniSerializer
