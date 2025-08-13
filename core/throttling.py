# core/throttling.py
from rest_framework.throttling import SimpleRateThrottle


class LessonRequestThrottle(SimpleRateThrottle):
    """
    Kullanıcı (auth ise user.pk, değilse IP) başına,
    SADECE ders talebi oluşturma (create/POST) işlemlerini rate limit eder.
    """
    scope = "lesson_request"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        ident = user.pk if (user and user.is_authenticated) else self.get_ident(request)
        if not ident:
            return None
        return self.cache_format % {"scope": self.scope, "ident": ident}

    def allow_request(self, request, view):
        # ViewSet ise action 'create', APIView ise method 'POST' kontrolü
        is_create_action = getattr(view, "action", None) == "create"
        is_post = request.method == "POST"
        if not (is_create_action or is_post):
            return True
        return super().allow_request(request, view)
