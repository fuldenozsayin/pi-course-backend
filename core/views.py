# core/views.py
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import F
from django_filters.rest_framework import FilterSet, filters
from rest_framework import generics, viewsets, mixins
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import Subject, LessonRequest
from .serializers import (
    RegisterSerializer,
    MeSerializer, MeUpdateSerializer,
    SubjectSerializer,
    TutorMiniSerializer, TutorDetailSerializer,
    LessonRequestCreateSerializer, LessonRequestListSerializer, LessonRequestStatusSerializer,
)

User = get_user_model()


# ---------- Auth ----------
@extend_schema(description="Kullanıcı kaydı (role: student|tutor).")
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        return token


@extend_schema(description="JWT ile giriş. access/refresh döner.")
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


# ---------- Me ----------
@extend_schema(description="Oturum sahibi profili (GET). Kısmî güncelleme (PATCH).")
class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        return MeUpdateSerializer if self.request.method in ("PUT", "PATCH") else MeSerializer


# ---------- Subject ----------
class SubjectViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Subject.objects.all().order_by("name")
    serializer_class = SubjectSerializer
    permission_classes = [AllowAny]


# ---------- Tutor list/detail + filtre/arama/sıralama ----------
class TutorFilter(FilterSet):
    subject = filters.NumberFilter(method="filter_subject")
    search = filters.CharFilter(method="filter_search")

    class Meta:
        model = User
        fields = []

    def filter_subject(self, qs, name, value):
        return qs.filter(tutorprofile__subjects__id=value)

    def filter_search(self, qs, name, value):
        return qs.filter(
            models.Q(first_name__icontains=value)
            | models.Q(last_name__icontains=value)
            | models.Q(tutorprofile__bio__icontains=value)
        )


class TutorViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    queryset = (
        User.objects.filter(role="tutor")
        .select_related("tutorprofile")
        .prefetch_related("tutorprofile__subjects")
    )
    filterset_class = TutorFilter
    search_fields = ["first_name", "last_name", "tutorprofile__bio"]
    ordering_fields = ["rating", "hourly_rate"]
    ordering = ["-rating"]

    # rating/hourly_rate alias'ları
    def get_queryset(self):
        return super().get_queryset().annotate(
            rating=F("tutorprofile__rating"),
            hourly_rate=F("tutorprofile__hourly_rate"),
        )

    def get_serializer_class(self):
        return TutorDetailSerializer if self.action == "retrieve" else TutorMiniSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(name="subject", description="Subject ID", required=False, type=int),
            OpenApiParameter(name="search", description="Ad/Bio arama", required=False, type=str),
            OpenApiParameter(
                name="ordering",
                description="Sıralama: rating | -rating | hourly_rate | -hourly_rate",
                required=False,
                type=str,
            ),
        ],
        description="Eğitmen listesi. Filtre: subject, Arama: search, Sıralama: ordering (örn. -rating).",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


# ---------- LessonRequest list/create/update ----------
class LessonRequestViewSet(
    viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.ListModelMixin, mixins.UpdateModelMixin
):
    queryset = LessonRequest.objects.all().select_related("student", "tutor", "subject")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return LessonRequestCreateSerializer
        if self.action in ("partial_update", "update"):
            return LessonRequestStatusSerializer
        return LessonRequestListSerializer

    def get_queryset(self):
        user = self.request.user
        role = self.request.query_params.get("role")
        status_q = self.request.query_params.get("status")

        qs = super().get_queryset()
        if role == "student" or (not role and user.role == "student"):
            qs = qs.filter(student=user)
        elif role == "tutor" or (not role and user.role == "tutor"):
            qs = qs.filter(tutor=user)
        else:
            qs = qs.none()

        if status_q:
            qs = qs.filter(status=status_q)
        return qs

    def perform_create(self, serializer):
        if self.request.user.role != "student":
            # 403 döndürmek için ValidationError yerine PermissionError control ediyoruz
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only students can create lesson requests.")
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role != "tutor" or instance.tutor_id != request.user.id:
            return Response({"detail": "Only the assigned tutor can change status."}, status=403)
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(name="role", description="Görünüm: student | tutor", required=False, type=OpenApiTypes.STR),
            OpenApiParameter(
                name="status", description="Durum: pending | approved | rejected", required=False, type=OpenApiTypes.STR
            ),
        ],
        description="Oturum sahibinin talepleri. Öğrenciyse kendi gönderdiği; eğitmense kendisine gelen talepler.",
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
