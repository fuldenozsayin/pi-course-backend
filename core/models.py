from django.contrib.auth.models import AbstractUser
from django.db import models

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
    def __str__(self): return self.name


class TutorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    hourly_rate = models.PositiveIntegerField(default=0)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    subjects = models.ManyToManyField(Subject, blank=True, related_name="tutors")
    def __str__(self): return f"TutorProfile<{self.user.email}>"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    grade_level = models.CharField(max_length=64, blank=True)
    def __str__(self): return f"StudentProfile<{self.user.email}>"


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

    class Meta:
        ordering = ["-created_at"]
