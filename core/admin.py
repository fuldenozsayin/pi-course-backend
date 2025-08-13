from django.contrib import admin
from .models import User, Subject, TutorProfile, StudentProfile, LessonRequest

admin.site.register(User)
admin.site.register(Subject)
admin.site.register(TutorProfile)
admin.site.register(StudentProfile)
admin.site.register(LessonRequest)
