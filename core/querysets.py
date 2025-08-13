# core/querysets.py
#Backend’de select_related / prefetch_related ile N+1 önleme. 
from django.db import models
from django.db.models import Prefetch

class TutorQuerySet(models.QuerySet):
    """
    Sık kullanılan ilişkileri tek noktadan toplayalım.
    - Tutor.user (OneToOne/ForeignKey) -> select_related
    - Tutor.subjects (M2M veya through) -> prefetch_related
    - Tutor.courses (varsa) -> prefetch_related
    """
    def with_user(self):
        return self.select_related("user")

    def with_subjects(self):
        # subjects ilişki adı projene göre "subjects" ya da "tutor_subjects" olabilir.
        return self.prefetch_related("subjects")

    def with_courses(self):
        # courses ilişkisi yoksa bu metodu kullanmazsın; varsa hazır.
        return self.prefetch_related("courses")

    def for_list(self):
        # Liste ekranı için en sık gereken kombinasyon
        return (self
                .with_user()
                .with_subjects())

class LessonRequestQuerySet(models.QuerySet):
    """
    N+1'ın en sık görüldüğü yer: talep listeleri.
    - student -> select_related
    - student.user -> select_related (zincir)
    - tutor -> select_related
    - tutor.user -> select_related
    - subject -> select_related
    """
    def for_list(self):
        return (self
                .select_related(
                    "student", "student__user",
                    "tutor", "tutor__user",
                    "subject"
                ))

class SubjectQuerySet(models.QuerySet):
    def with_tutors(self):
        # Konu -> Eğitmenler sayfası/endpoint’i varsa
        return self.prefetch_related(
            Prefetch("tutors", queryset=TutorQuerySet(self.model._default_manager.model.objects.all()).with_user())
        )
