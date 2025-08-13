from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.cache import cache


class SmokeTest(TestCase):
    def test_truth(self):
        self.assertTrue(True)


class AuthAndLessonFlowTests(APITestCase):
    def setUp(self):
        # Her testten önce throttle sayaçlarını temizle
        cache.clear()

    def register(self, email: str, password: str, role: str):
        url = "/auth/register"  # API prefix yok, core/urls.py’ye göre
        payload = {
            "username": email.split("@")[0],
            "email": email,
            "password": password,
            "role": role
        }
        res = self.client.post(url, payload, format="json")
        self.assertIn(res.status_code, (status.HTTP_200_OK, status.HTTP_201_CREATED), msg=getattr(res, "data", res.content))
        return res

    def login(self, email: str, password: str):
        url = "/auth/login"
        payload = {
            "email": email,
            "password": password
        }
        res = self.client.post(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK, msg=getattr(res, "data", res.content))
        return res.data["access"]

    def test_full_lesson_request_flow(self):
        tutor_email = "tutor@example.com"
        student_email = "student@example.com"
        password = "testpass123"

        # Tutor kaydı
        self.register(tutor_email, password, role="tutor")
        tutor_token = self.login(tutor_email, password)

        # Student kaydı
        self.register(student_email, password, role="student")
        student_token = self.login(student_email, password)

        # Tutor profiline subject ekle
        res_subjects = self.client.get("/subjects/")
        self.assertEqual(res_subjects.status_code, status.HTTP_200_OK)
        subject_id = res_subjects.data[0]["id"]

        tutor_profile_payload = {
            "bio": "Experienced tutor",
            "hourly_rate": 100,
            "subjects": [subject_id]
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tutor_token}")
        res_update_tutor = self.client.put("/tutors/me/", tutor_profile_payload, format="json")
        self.assertEqual(res_update_tutor.status_code, status.HTTP_200_OK, msg=getattr(res_update_tutor, "data", res_update_tutor.content))

        # Student, tutor'a ders talebi oluşturur
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {student_token}")
        lesson_payload = {
            "tutor": res_update_tutor.data["id"],
            "subject": subject_id,
            "start_time": "2025-08-20T10:00:00Z",
            "duration_minutes": 60
        }
        res_create = self.client.post("/lesson-requests/", lesson_payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED, msg=getattr(res_create, "data", res_create.content))
        lr_id = res_create.data["id"]

        # Tutor talebi onaylar
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tutor_token}")
        res_approve = self.client.patch(f"/lesson-requests/{lr_id}/", {"status": "approved"}, format="json")
        self.assertEqual(res_approve.status_code, status.HTTP_200_OK, msg=getattr(res_approve, "data", res_approve.content))

    def test_permissions_student_cannot_approve(self):
        tutor_email = "tutor2@example.com"
        student_email = "student2@example.com"
        password = "testpass123"

        # Tutor kaydı
        self.register(tutor_email, password, role="tutor")
        tutor_token = self.login(tutor_email, password)

        # Student kaydı
        self.register(student_email, password, role="student")
        student_token = self.login(student_email, password)

        # Tutor profiline subject ekle
        res_subjects = self.client.get("/subjects/")
        self.assertEqual(res_subjects.status_code, status.HTTP_200_OK)
        subject_id = res_subjects.data[0]["id"]

        tutor_profile_payload = {
            "bio": "Experienced tutor",
            "hourly_rate": 100,
            "subjects": [subject_id]
        }
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tutor_token}")
        res_update_tutor = self.client.put("/tutors/me/", tutor_profile_payload, format="json")
        self.assertEqual(res_update_tutor.status_code, status.HTTP_200_OK, msg=getattr(res_update_tutor, "data", res_update_tutor.content))

        # Student, tutor'a ders talebi oluşturur
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {student_token}")
        lesson_payload = {
            "tutor": res_update_tutor.data["id"],
            "subject": subject_id,
            "start_time": "2025-08-20T10:00:00Z",
            "duration_minutes": 60
        }
        res_create = self.client.post("/lesson-requests/", lesson_payload, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED, msg=getattr(res_create, "data", res_create.content))
        lr_id = res_create.data["id"]

        # Student onaylamaya çalışır (yetkisi olmamalı)
        res_approve = self.client.patch(f"/lesson-requests/{lr_id}/", {"status": "approved"}, format="json")
        self.assertEqual(res_approve.status_code, status.HTTP_403_FORBIDDEN, msg=getattr(res_approve, "data", res_approve.content))
