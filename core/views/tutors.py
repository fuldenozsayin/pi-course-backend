# core/views/tutors.py
#Backend’de select_related / prefetch_related ile N+1 önleme. 
from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny
from django.db.models import Q

from core.models import Tutor
from core.serializers import TutorListSerializer, TutorDetailSerializer

class TutorViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    lookup_field = "pk"

    def get_queryset(self):
        qs = Tutor.objects.for_list()  # select_related(user) + prefetch(subjects)

        # Basit filtre/sıralama örnekleri (mobilde kullanılıyor olabilir)
        subject_id = self.request.query_params.get("subjectId")
        search = self.request.query_params.get("search")
        ordering = self.request.query_params.get("ordering", "-id")

        if subject_id:
            qs = qs.filter(subjects__id=subject_id)

        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__username__icontains=search) |
                Q(bio__icontains=search)
            )

        return qs.order_by(ordering).distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TutorDetailSerializer
        return TutorListSerializer
