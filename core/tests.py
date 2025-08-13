from django.test import TestCase
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Subject, TutorProfile, StudentProfile, LessonRequest

User = get_user_model()


# Basit smoke test
class SmokeTest(TestCase):
    def test_truth(self):
        self.assertTrue(True)


class AuthAndLessonFlowTests(APITestCase):
    def setUp(self):
        # Throttle sayaçları temizlensin
        cache.clear()

    # ---------- Helpers ----------
    def register(self, email: str, password: str, role: str):
        url = "/api/auth/register"
        payload = {
            "username": email.split("@")[0],  # backend username istiyor
            "email": email,
            "password": password,
            "role": role,
        }
        res = self.client.post(url, payload, format="json")
        self.assertIn(
            res.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED),
            msg=getattr(res, "data", res.content),
        )
        return res

    def login(self, email: str, password: str) -> str:
        url = "/api/auth/login"
        payload = {"email": email, "password": password}
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, msg=getattr(res, "data", res.content))
        self.assertIn("access", res.data)
        return res.data["access"]

    def ensure_subject_id(self) -> int:
        """
        /api/subjects/ sayfalı ({"count":..,"results":[...]}) veya düz liste dönebilir.
        Boşsa ORM ile bir Subject yaratır ve id'yi döner.
        """
        res = self.client.get("/api/subjects/")
        self.assertEqual(res.status_code, status.HTTP_200_OK, msg=getattr(res, "data", res.content))
        data = res.data
        if isinstance(data, dict):
            items = data.get("results", [])
        else:
            items = data

        if not items:
            subj = Subject.objects.create(name="Physics")
            return subj.id
        return items[0]["id"]

    def attach_subject_to_tutor(self, tutor_email: str, subject_id: int):
        tutor = User.objects.get(email=tutor_email)
        # Profil oluşmadıysa bu satır hata verir; senin projende sinyalle oluşuyor varsayımı.
        tprof = TutorProfile.objects.get(user=tutor)
        tprof.subjects.add(Subject.objects.get(id=subject_id))

    def auth_bearer(self, token: str):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ---------- Tests ----------
    def test_full_lesson_request_flow(self):
        tutor_email = "tutor@example.com"
        student_email = "student@example.com"
        password = "testpass123"

        # Kayıt + login
        self.register(tutor_email, password, role="tutor")
        self.register(student_email, password, role="student")
        tutor_token = self.login(tutor_email, password)
        student_token = self.login(student_email, password)

        # Subject hazırla ve tutora iliştir
        subject_id = self.ensure_subject_id()
        self.attach_subject_to_tutor(tutor_email, subject_id)

        # Student -> ders talebi oluştur
        self.auth_bearer(student_token)
        start_time = (timezone.now() + timezone.timedelta(days=1)).isoformat().replace("+00:00", "Z")
        payload = {
            "tutor_id": User.objects.get(email=tutor_email).id,
            "subject_id": subject_id,
            "start_time": start_time,
            "duration_minutes": 60,
            "note": "Kuantum giriş",
        }
        res_create = self.client.post("/api/lesson-requests/", payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED, msg=getattr(res_create, "data", res_create.content))
        lr_id = res_create.data["id"]

        lr = LessonRequest.objects.get(id=lr_id)
        self.assertEqual(lr.status, "pending")

        # Tutor -> approve
        self.auth_bearer(tutor_token)
        res_approve = self.client.patch(f"/api/lesson-requests/{lr_id}/", {"status": "approved"}, format="json")
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK, msg=getattr(res_approve, "data", res_approve.content))
        lr.refresh_from_db()
        self.assertEqual(lr.status, "approved")

    def test_permissions_student_cannot_approve(self):
        tutor_email = "tutor2@example.com"
        student_email = "student2@example.com"
        password = "testpass123"

        # Kayıt + login
        self.register(tutor_email, password, role="tutor")
        self.register(student_email, password, role="student")
        tutor_token = self.login(tutor_email, password)
        student_token = self.login(student_email, password)

        # Subject hazırla ve tutora iliştir
        subject_id = self.ensure_subject_id()
        self.attach_subject_to_tutor(tutor_email, subject_id)

        # Student -> ders talebi oluştur
        self.auth_bearer(student_token)
        start_time = (timezone.now() + timezone.timedelta(days=2)).isoformat().replace("+00:00", "Z")
        payload = {
            "tutor_id": User.objects.get(email=tutor_email).id,
            "subject_id": subject_id,
            "start_time": start_time,
            "duration_minutes": 45,
        }
        res_create = self.client.post("/api/lesson-requests/", payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED, msg=getattr(res_create, "data", res_create.content))
        lr_id = res_create.data["id"]

        # Student approve etmeye çalışır -> 403 beklenir
        res_approve = self.client.patch(f"/api/lesson-requests/{lr_id}/", {"status": "approved"}, format="json")
        self.assertEqual(res_approve.status_code, status.HTTP_403_FORBIDDEN, msg=getattr(res_approve, "data", res_approve.content))
