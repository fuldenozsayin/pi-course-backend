from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Subject, TutorProfile, StudentProfile, LessonRequest

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    class Meta:
        model = User
        fields = ["id", "email", "username", "role", "password"]
    def create(self, validated_data):
        pwd = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(pwd)
        user.save()
        if user.role == "tutor":
            TutorProfile.objects.create(user=user)
        else:
            StudentProfile.objects.create(user=user)
        return user

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ["id", "name"]

class TutorMiniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    subjects = SubjectSerializer(many=True, source="tutorprofile.subjects")
    hourly_rate = serializers.IntegerField(source="tutorprofile.hourly_rate")
    rating = serializers.DecimalField(source="tutorprofile.rating", max_digits=2, decimal_places=1)
    bio = serializers.CharField(source="tutorprofile.bio")
    class Meta:
        model = User
        fields = ["id", "name", "subjects", "hourly_rate", "rating", "bio"]
    def get_name(self, obj):
        return obj.get_full_name() or obj.username or obj.email

class TutorDetailSerializer(TutorMiniSerializer):
    pass

class MeSerializer(serializers.ModelSerializer):
    tutorprofile = serializers.SerializerMethodField()
    studentprofile = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ["id","email","username","first_name","last_name","role","tutorprofile","studentprofile"]
    def get_tutorprofile(self, obj):
        tp = getattr(obj, "tutorprofile", None)
        if not tp: return None
        return {
            "bio": tp.bio, "hourly_rate": tp.hourly_rate, "rating": tp.rating,
            "subjects": SubjectSerializer(tp.subjects.all(), many=True).data,
        }
    def get_studentprofile(self, obj):
        sp = getattr(obj, "studentprofile", None)
        if not sp: return None
        return {"grade_level": sp.grade_level}

class MeUpdateSerializer(serializers.Serializer):
    bio = serializers.CharField(required=False, allow_blank=True)
    hourly_rate = serializers.IntegerField(required=False)
    grade_level = serializers.CharField(required=False, allow_blank=True)
    subjects = serializers.ListField(child=serializers.IntegerField(), required=False)
    def update(self, instance, validated):
        if instance.role == "tutor":
            tp = instance.tutorprofile
            if "bio" in validated: tp.bio = validated["bio"]
            if "hourly_rate" in validated: tp.hourly_rate = validated["hourly_rate"]
            if "subjects" in validated:
                tp.subjects.set(Subject.objects.filter(id__in=validated["subjects"]))
            tp.save()
        else:
            sp = instance.studentprofile
            if "grade_level" in validated: sp.grade_level = validated["grade_level"]
            sp.save()
        return instance

class LessonRequestCreateSerializer(serializers.ModelSerializer):
    tutor_id = serializers.IntegerField(write_only=True)
    subject_id = serializers.IntegerField(write_only=True)
    class Meta:
        model = LessonRequest
        fields = ["id","tutor_id","subject_id","start_time","duration_minutes","note"]
    def validate(self, attrs):
        if self.context["request"].user.role != "student":
            raise serializers.ValidationError("Only students can create lesson requests.")
        return attrs
    def create(self, validated):
        user = self.context["request"].user
        tutor = User.objects.get(id=validated.pop("tutor_id"), role="tutor")
        subject = Subject.objects.get(id=validated.pop("subject_id"))
        return LessonRequest.objects.create(student=user, tutor=tutor, subject=subject, **validated)

class LessonRequestListSerializer(serializers.ModelSerializer):
    student_email = serializers.EmailField(source="student.email", read_only=True)
    tutor_email = serializers.EmailField(source="tutor.email", read_only=True)
    subject = SubjectSerializer(read_only=True)
    class Meta:
        model = LessonRequest
        fields = ["id","student_email","tutor_email","subject","start_time","duration_minutes","status","note","created_at"]

class LessonRequestStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonRequest
        fields = ["status"]
