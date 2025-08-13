from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Subject, TutorProfile, StudentProfile

User = get_user_model()

class Command(BaseCommand):
    help = "Seed demo data"

    def handle(self, *args, **kwargs):
        # Dersler
        math, _ = Subject.objects.get_or_create(name="Math")
        physics, _ = Subject.objects.get_or_create(name="Physics")
        english, _ = Subject.objects.get_or_create(name="English")

        # Tutor 1
        tutor1, created = User.objects.get_or_create(
            email="tutor@demo.com",
            defaults={"username": "tutor", "role": "tutor"}
        )
        tutor1.set_password("Passw0rd!")
        tutor1.save()
        tp1, _ = TutorProfile.objects.get_or_create(
            user=tutor1,
            defaults={"bio": "ODTÜ fizik doktora", "hourly_rate": 500, "rating": 4.8}
        )
        tp1.subjects.set([physics, math])

        # Tutor 2
        tutor2, created = User.objects.get_or_create(
            email="tutor2@demo.com",
            defaults={"username": "tutor2", "role": "tutor"}
        )
        tutor2.set_password("Passw0rd!")
        tutor2.save()
        tp2, _ = TutorProfile.objects.get_or_create(
            user=tutor2,
            defaults={"bio": "Deneyimli hoca", "hourly_rate": 400, "rating": 4.5}
        )
        tp2.subjects.set([english])

        # Student
        student, created = User.objects.get_or_create(
            email="student@demo.com",
            defaults={"username": "student", "role": "student"}
        )
        student.set_password("Passw0rd!")
        student.save()
        StudentProfile.objects.get_or_create(
            user=student,
            defaults={"grade_level": "11"}
        )

        self.stdout.write(self.style.SUCCESS("Demo veriler başarıyla eklendi."))
