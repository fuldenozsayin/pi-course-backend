#Backend’de select_related / prefetch_related ile N+1 önleme. 
from rest_framework import viewsets, mixins, permissions
from core.models import Subject
from core.serializers import SubjectSerializer

class SubjectViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = SubjectSerializer
    lookup_field = "id"

    def get_queryset(self):
        # Subject listesi basit; N+1 yok. İlerde subject->tutors döneceksen:
        # return Subject.objects.prefetch_related("tutors", "tutors__user")
        return Subject.objects.all().order_by("name")
