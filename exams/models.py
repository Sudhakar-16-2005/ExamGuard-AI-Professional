import hashlib

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ExamType(models.Model):
    class Scope(models.TextChoices):
        NEET = "neet", "NEET"
        JEE = "jee", "JEE"
        STATE_BOARD = "state_board", "State board public exam"
        UNIVERSITY = "university", "University semester exam"
        OTHER = "other", "Other examination"

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30, unique=True)
    scope = models.CharField(max_length=24, choices=Scope.choices)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default matching, language and workflow settings.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.code} · {self.name}"


class Exam(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    authority = models.ForeignKey(
        "authorities.Authority", on_delete=models.PROTECT, related_name="exams"
    )
    exam_type = models.ForeignKey(
        ExamType, on_delete=models.PROTECT, related_name="exams"
    )
    name = models.CharField(max_length=180)
    code = models.CharField(max_length=50, unique=True)
    academic_year = models.CharField(max_length=12)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    languages = models.JSONField(default=list, blank=True)
    similarity_threshold = models.FloatField(
        default=0.55, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    critical_threshold = models.FloatField(
        default=0.78, validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    config = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-starts_at",)
        indexes = [models.Index(fields=("status", "starts_at"))]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError(
                {"ends_at": "The end time must be after the start time."}
            )
        if self.critical_threshold < self.similarity_threshold:
            raise ValidationError(
                {
                    "critical_threshold": "Critical threshold must be greater than or equal to review threshold."
                }
            )

    def __str__(self):
        return f"{self.code} · {self.name}"


class Paper(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready for comparison"
        ARCHIVED = "archived", "Archived"

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="papers")
    subject = models.CharField(max_length=140)
    paper_code = models.CharField(max_length=60)
    set_code = models.CharField(max_length=30, blank=True)
    language = models.CharField(max_length=30, default="English")
    reference_file = models.FileField(upload_to="reference_papers/%Y/%m/", blank=True)
    extracted_text = models.TextField(blank=True, editable=False)
    sha256 = models.CharField(max_length=64, blank=True, editable=False, db_index=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("exam", "subject", "paper_code")
        constraints = [
            models.UniqueConstraint(
                fields=("exam", "paper_code", "set_code"), name="unique_exam_paper_set"
            )
        ]

    def compute_hash(self):
        if not self.reference_file:
            return ""
        hasher = hashlib.sha256()
        self.reference_file.open("rb")
        try:
            for chunk in self.reference_file.chunks():
                hasher.update(chunk)
        finally:
            self.reference_file.close()
        return hasher.hexdigest()

    def __str__(self):
        return f"{self.exam.code} · {self.subject} · {self.paper_code}"


class Question(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="questions")
    number = models.CharField(max_length=20)
    text = models.TextField()
    marks = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    fingerprint = models.CharField(
        max_length=64, blank=True, editable=False, db_index=True
    )
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("paper", "number")
        constraints = [
            models.UniqueConstraint(
                fields=("paper", "number"), name="unique_question_number_per_paper"
            )
        ]

    def save(self, *args, **kwargs):
        normalized = " ".join(self.text.lower().split())
        self.fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.paper.paper_code} · Q{self.number}"
