# core/admin.py
from django.contrib import admin
from .models import User, Subject, TutorProfile, StudentProfile, LessonRequest


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "username", "role")
    search_fields = ("email", "username", "first_name", "last_name")
    list_filter = ("role",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(TutorProfile)
class TutorProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "hourly_rate", "rating")
    list_select_related = ("user",)
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    filter_horizontal = ("subjects",)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "grade_level")
    list_select_related = ("user",)
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")


@admin.register(LessonRequest)
class LessonRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "tutor", "subject", "status", "created_at")
    list_select_related = ("student", "tutor", "subject")
    search_fields = (
        "student__email", "student__username",
        "tutor__email", "tutor__username",
        "subject__name",
    )
    list_filter = ("status", "subject")
