from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterView, LoginView, MeView, SubjectViewSet, TutorViewSet, LessonRequestViewSet

router = DefaultRouter()
router.register("subjects", SubjectViewSet, basename="subject")
router.register("tutors", TutorViewSet, basename="tutor")
router.register("lesson-requests", LessonRequestViewSet, basename="lesson-request")

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="register"),
    path("auth/login", LoginView.as_view(), name="login"),
    path("me", MeView.as_view(), name="me"),
    path("", include(router.urls)),
]
