# core/views.py
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import viewsets, mixins, permissions, generics, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Subject, LessonRequest
from .serializers import (
    RegisterSerializer,
    SubjectSerializer,
    TutorMiniSerializer,
    TutorDetailSerializer,
    MeSerializer,
    MeUpdateSerializer,
    LessonRequestCreateSerializer,
    LessonRequestListSerializer,
    LessonRequestStatusSerializer,
)

User = get_user_model()


# -------------------------
# Auth
# -------------------------
class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register
    body: { email, username, role: student|tutor, password }
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login
    body: { email, password }
    response: { access, refresh }
    """
    permission_classes = [permissions.AllowAny]


# -------------------------
# Me (profil)
# -------------------------
class MeView(generics.GenericAPIView):
    """
    GET /api/me
    PATCH /api/me
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # N+1 önleme: profil ve subjects'i tek hamlede getir
        user = (
            User.objects.filter(id=request.user.id)
            .select_related("tutorprofile", "studentprofile")
            .prefetch_related("tutorprofile__subjects")
            .get()
        )
        return Response(MeSerializer(user).data)

    def patch(self, request):
        ser = MeUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.update(request.user, ser.validated_data)

        # Güncel değeri optimize şekilde tekrar oku
        user = (
            User.objects.filter(id=request.user.id)
            .select_related("tutorprofile", "studentprofile")
            .prefetch_related("tutorprofile__subjects")
            .get()
        )
        return Response(MeSerializer(user).data, status=status.HTTP_200_OK)


# -------------------------
# Subject
# -------------------------
class SubjectViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    """
    GET /api/subjects
    GET /api/subjects/{id}
    """
    queryset = Subject.objects.all().order_by("name")
    serializer_class = SubjectSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "id"


# -------------------------
# Tutors
# -------------------------
class TutorViewSet(mixins.ListModelMixin,
                   mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    """
    GET /api/tutors?subject=<id>&ordering=-rating&search=<q>
    GET /api/tutors/{id}
    """
    permission_classes = [permissions.AllowAny]
    lookup_field = "id"

    def get_queryset(self):
        """
        N+1 önleme:
        - O2O: tutorprofile -> select_related
        - M2M: tutorprofile.subjects -> prefetch_related
        """
        qs = (
            User.objects.filter(role="tutor")
            .select_related("tutorprofile")
            .prefetch_related("tutorprofile__subjects")
        )

        # Filtreler
        subject_id = self.request.query_params.get("subject")
        if subject_id:
            qs = qs.filter(tutorprofile__subjects__id=subject_id)

        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(tutorprofile__bio__icontains=search)
            )

        # Sıralama (güvenli harita)
        requested = self.request.query_params.get("ordering") or "-rating"
        safe_order_map = {
            "rating": "tutorprofile__rating",
            "-rating": "-tutorprofile__rating",
            "hourly_rate": "tutorprofile__hourly_rate",
            "-hourly_rate": "-tutorprofile__hourly_rate",
            "id": "id",
            "-id": "-id",
        }
        ordering = safe_order_map.get(requested, "-tutorprofile__rating")
        return qs.order_by(ordering).distinct()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TutorDetailSerializer
        return TutorMiniSerializer


# -------------------------
# Lesson Requests
# -------------------------
class LessonRequestViewSet(mixins.ListModelMixin,
                           mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           viewsets.GenericViewSet):
    """
    GET /api/lesson-requests?role=student|tutor&status=pending|approved|rejected
    POST /api/lesson-requests
    PATCH /api/lesson-requests/{id} (sadece ilgili tutor status günceller)
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        """
        N+1 önleme:
        - FK: student, tutor, subject -> select_related
        """
        base = LessonRequest.objects.select_related("student", "tutor", "subject")

        user = self.request.user
        role_q = self.request.query_params.get("role")

        # Kendi perspektifine göre daralt
        if role_q == "student" or user.role == "student":
            qs = base.filter(student=user)
        elif role_q == "tutor" or user.role == "tutor":
            qs = base.filter(tutor=user)
        else:
            # admin değilse yine kendi kayıtlarını görsün
            qs = base.filter(Q(student=user) | Q(tutor=user))

        status_q = self.request.query_params.get("status")
        if status_q:
            qs = qs.filter(status=status_q)

        return qs.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "create":
            return LessonRequestCreateSerializer
        if self.action in ("update", "partial_update"):
            return LessonRequestStatusSerializer
        return LessonRequestListSerializer

    def perform_update(self, serializer):
        """
        Status güncelleme yetkisi: sadece ilgili 'tutor' kullanıcı.
        """
        instance = self.get_object()
        if self.request.user != instance.tutor:
            raise PermissionDenied("Only the related tutor can update the status.")
        serializer.save()

    # Opsiyonel: ayrı bir status endpoint'i de istersen
    @action(methods=["patch"], detail=True, url_path="status")
    def set_status(self, request, id=None):
        instance = self.get_object()
        if request.user != instance.tutor:
            raise PermissionDenied("Only the related tutor can update the status.")
        ser = LessonRequestStatusSerializer(instance, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        # Güncel kaydı select_related ile geri gönder
        refreshed = (
            LessonRequest.objects.select_related("student", "tutor", "subject")
            .get(id=instance.id)
        )
        return Response(LessonRequestListSerializer(refreshed).data, status=status.HTTP_200_OK)
