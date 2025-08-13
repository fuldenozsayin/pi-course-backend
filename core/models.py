# core/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


# -----------------------------
# QuerySet Helper'ları (N+1 önleme)
# -----------------------------
class TutorProfileQuerySet(models.QuerySet):
    """
    TutorProfile -> user (FK/O2O): select_related
    TutorProfile -> subjects (M2M): prefetch_related
    """
    def with_user(self):
        return self.select_related("user")

    def with_subjects(self):
        return self.prefetch_related("subjects")

    def for_list(self):
        # Liste ekranlarında çoğunlukla bu kombinasyon yeterli
        return self.with_user().with_subjects()


class StudentProfileQuerySet(models.QuerySet):
    def with_user(self):
        return self.select_related("user")


class LessonRequestQuerySet(models.QuerySet):
    """
    LessonRequest -> student (User), tutor (User), subject (FK): select_related
    Not: Student/Tutor profillerine de ihtiyaç olursa, reverse O2O oldukları için
    prefetch_related('student__studentprofile', 'tutor__tutorprofile') eklenebilir.
    """
    def for_list(self):
        return self.select_related("student", "tutor", "subject")


class SubjectQuerySet(models.QuerySet):
    def with_tutors(self):
        # İleri seviye: Subject -> tutors (TutorProfile) + onların user'ı
        # Çok geniş listelerde dikkatli kullan; yine de N+1'ı kırar.
        return self.prefetch_related(
            models.Prefetch(
                "tutors",
                queryset=TutorProfile.objects.for_list()
            )
        )


# -----------------------------
# Modeller
# -----------------------------
class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TUTOR = "tutor", "Tutor"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=Role.choices)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]  # createsuperuser için

    def __str__(self):
        return f"{self.email} ({self.role})"


class Subject(models.Model):
    name = models.CharField(max_length=64, unique=True)

    # N+1 azaltma için özel manager
    objects = SubjectQuerySet.as_manager()

    def __str__(self):
        return self.name


class TutorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    hourly_rate = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="tutors")

    # N+1 azaltma için özel manager
    objects = TutorProfileQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["rating"]),
            models.Index(fields=["hourly_rate"]),
        ]

    def __str__(self):
        return f"TutorProfile<{self.user.email}>"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    grade_level = models.CharField(max_length=64, blank=True)

    # N+1 azaltma için özel manager
    objects = StudentProfileQuerySet.as_manager()

    def __str__(self):
        return f"StudentProfile<{self.user.email}>"


class LessonRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_requests")
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_requests")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    start_time = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # N+1 azaltma için özel manager
    objects = LessonRequestQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["start_time"]),
        ]

    def __str__(self):
        return f"{self.student.email} -> {self.tutor.email} ({self.subject.name})"
