from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Subject, TutorProfile, StudentProfile, LessonRequest

User = get_user_model()


# Basit smoke test (CI tetik testi)
class SmokeTest(TestCase):
    def test_truth(self):
        self.assertTrue(True)


# Entegrasyon testleri
def auth(client, token: str):
    """APIClient için Authorization header'ını ayarla."""
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")


class AuthAndLessonFlowTests(APITestCase):
    """
    Kritik akış testleri:
    - Kullanıcı kayıt + login
    - Rol izinleri (403 senaryoları)
    - Ders talebi oluşturma ve onaylama
    """

    @classmethod
    def setUpTestData(cls):
        cls.subject = Subject.objects.create(name="Physics")

    def register(self, email: str, password: str, role: str):
        url = "/api/auth/register"
        payload = {"email": email, "password": password, "role": role}
        res = self.client.post(url, payload, format="json")
        self.assertIn(res.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), msg=res.data)
        return res

    def login(self, email: str, password: str) -> str:
        url = "/api/auth/login"
        payload = {"email": email, "password": password}
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, msg=res.data)
        self.assertIn("access", res.data)
        return res.data["access"]

    def test_full_lesson_request_flow(self):
        # 1) Tutor ve Student kayıt
        tutor_email = "tutor@test.com"
        student_email = "student@test.com"
        password = "Passw0rd!"

        self.register(tutor_email, password, role="tutor")
        self.register(student_email, password, role="student")

        self.assertTrue(TutorProfile.objects.filter(user__email=tutor_email).exists())
        self.assertTrue(StudentProfile.objects.filter(user__email=student_email).exists())

        tutor_user = User.objects.get(email=tutor_email)
        student_user = User.objects.get(email=student_email)

        TutorProfile.objects.get(user=tutor_user).subjects.add(self.subject)

        tutor_token = self.login(tutor_email, password)
        student_token = self.login(student_email, password)

        # 2) Student ders talebi oluşturur
        start_time = timezone.now() + timezone.timedelta(days=1)
        payload = {
            "tutor_id": tutor_user.id,
            "subject_id": self.subject.id,
            "start_time": start_time.isoformat().replace("+00:00", "Z"),
            "duration_minutes": 60,
            "note": "Kuantum giriş"
        }

        auth(self.client, student_token)
        res_create = self.client.post("/api/lesson-requests", payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED, msg=res_create.data)
        lr_id = res_create.data["id"]

        lr = LessonRequest.objects.get(id=lr_id)
        self.assertEqual(lr.student_id, student_user.id)
        self.assertEqual(lr.tutor_id, tutor_user.id)
        self.assertEqual(lr.subject_id, self.subject.id)
        self.assertEqual(lr.status, "pending")

        # 3) Tutor talebi approve eder
        auth(self.client, tutor_token)
        res_patch = self.client.patch(f"/api/lesson-requests/{lr_id}", {"status": "approved"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK, msg=res_patch.data)

        lr.refresh_from_db()
        self.assertEqual(lr.status, "approved")

    def test_permissions_student_cannot_approve(self):
        tutor_email = "perm_tutor@test.com"
        student_email = "perm_student@test.com"
        password = "Passw0rd!"

        self.register(tutor_email, password, role="tutor")
        self.register(student_email, password, role="student")

        tutor_user = User.objects.get(email=tutor_email)
        TutorProfile.objects.get(user=tutor_user).subjects.add(self.subject)

        tutor_token = self.login(tutor_email, password)
        student_token = self.login(student_email, password)

        start_time = timezone.now() + timezone.timedelta(days=2)
        payload = {
            "tutor_id": tutor_user.id,
            "subject_id": self.subject.id,
            "start_time": start_time.isoformat().replace("+00:00", "Z"),
            "duration_minutes": 45,
        }

        auth(self.client, student_token)
        res_create = self.client.post("/api/lesson-requests", payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        lr_id = res_create.data["id"]

        # Öğrenci approve etmeye çalışır → 403
        res_patch = self.client.patch(f"/api/lesson-requests/{lr_id}", {"status": "approved"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_403_FORBIDDEN)
