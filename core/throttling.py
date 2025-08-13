from rest_framework.throttling import SimpleRateThrottle

class LessonRequestThrottle(SimpleRateThrottle):
    scope = "lesson_request"

    def get_cache_key(self, request, view):
        # Auth varsa kullanıcı ID, yoksa IP ile kısıtla
        ident = request.user.pk if request.user.is_authenticated else self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}