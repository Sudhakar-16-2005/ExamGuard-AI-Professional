import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Source(models.Model):
    class Type(models.TextChoices):
        WEBSITE = "website", "Public website"
        RSS = "rss", "RSS/Atom feed"
        SEARCH_FEED = "search_feed", "Search/API feed"
        TELEGRAM_BOT = "telegram_bot", "Telegram Bot API"
        TELEGRAM_MTPROTO = "telegram_mtproto", "Telegram public/authorized client"
        WHATSAPP = "whatsapp", "WhatsApp Business webhook"
        MANUAL = "manual", "Manual submission"

    class Scope(models.TextChoices):
        PUBLIC = "public", "Publicly accessible"
        AUTHORIZED_PRIVATE = "authorized_private", "Private and explicitly authorized"
        OWNED_TEST = "owned_test", "Owned test source"

    name = models.CharField(max_length=160)
    source_type = models.CharField(max_length=24, choices=Type.choices, db_index=True)
    access_scope = models.CharField(
        max_length=24, choices=Scope.choices, default=Scope.PUBLIC
    )
    endpoint = models.CharField(
        max_length=500,
        blank=True,
        help_text="Public URL, channel username/chat ID, or WhatsApp phone-number ID.",
    )
    authority = models.ForeignKey(
        "authorities.Authority",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sources",
    )
    is_enabled = models.BooleanField(default=True, db_index=True)
    authorization_confirmed = models.BooleanField(default=False)
    authorization_note = models.TextField(blank=True)
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorized_sources",
    )
    authorized_at = models.DateTimeField(null=True, blank=True)
    terms_note = models.TextField(blank=True)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Keywords, exam filters, request interval and non-secret connector settings.",
    )
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("source_type", "name")
        indexes = [models.Index(fields=("source_type", "is_enabled"))]

    def clean(self):
        if self.access_scope != self.Scope.PUBLIC and not self.authorization_confirmed:
            raise ValidationError(
                {
                    "authorization_confirmed": "Private or test sources require explicit authorization confirmation."
                }
            )
        if self.access_scope != self.Scope.PUBLIC and not self.authorization_note:
            raise ValidationError(
                {
                    "authorization_note": "Document who granted access and the permitted monitoring purpose."
                }
            )

    def save(self, *args, **kwargs):
        if self.authorization_confirmed and not self.authorized_at:
            self.authorized_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_source_type_display()} · {self.name}"


class Upload(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        IGNORED = "ignored", "Ignored"

    source = models.ForeignKey(Source, on_delete=models.PROTECT, related_name="uploads")
    external_id = models.CharField(max_length=255, blank=True)
    original_url = models.URLField(max_length=1000, blank=True)
    sender_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="Platform pseudonymous identifier; avoid unnecessary personal data.",
    )
    content_type = models.CharField(max_length=120, blank=True)
    evidence_file = models.FileField(upload_to="evidence/%Y/%m/%d/", blank=True)
    raw_text = models.TextField(blank=True)
    extracted_text = models.TextField(blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RECEIVED, db_index=True
    )
    metadata = models.JSONField(default=dict, blank=True)
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-captured_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("source", "external_id"),
                condition=~models.Q(external_id=""),
                name="unique_external_item_per_source",
            )
        ]
        indexes = [models.Index(fields=("status", "captured_at"))]

    def __str__(self):
        return f"Upload {self.pk or 'new'} · {self.source.name}"


class Match(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending human review"
        CONFIRMED = "confirmed", "Confirmed leak"
        FALSE_POSITIVE = "false_positive", "False positive"
        DISMISSED = "dismissed", "Dismissed"

    upload = models.ForeignKey(Upload, on_delete=models.CASCADE, related_name="matches")
    paper = models.ForeignKey(
        "exams.Paper", on_delete=models.PROTECT, related_name="matches"
    )
    question = models.ForeignKey(
        "exams.Question",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matches",
    )
    similarity_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(1)], db_index=True
    )
    algorithm = models.CharField(max_length=80, default="tfidf-word-char-v1")
    matched_excerpt = models.TextField(blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-similarity_score", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("upload", "paper", "question"),
                name="unique_upload_paper_question_match",
            )
        ]

    def __str__(self):
        return f"{self.similarity_score:.1%} · {self.paper}"


class Incident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        NEW = "new", "New"
        TRIAGE = "triage", "Under triage"
        INVESTIGATING = "investigating", "Investigating"
        CONTAINED = "contained", "Contained"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    incident_code = models.CharField(max_length=40, unique=True, editable=False)
    match = models.OneToOneField(
        Match, on_delete=models.SET_NULL, null=True, blank=True, related_name="incident"
    )
    exam = models.ForeignKey(
        "exams.Exam", on_delete=models.PROTECT, related_name="incidents"
    )
    title = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    severity = models.CharField(
        max_length=12, choices=Severity.choices, default=Severity.MEDIUM, db_index=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_incidents",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_incidents",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    evidence = models.JSONField(default=dict, blank=True)
    response_actions = models.JSONField(default=list, blank=True)
    detected_at = models.DateTimeField(default=timezone.now, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-detected_at",)
        indexes = [models.Index(fields=("severity", "status", "detected_at"))]

    def save(self, *args, **kwargs):
        if not self.incident_code:
            self.incident_code = (
                f"EGA-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.incident_code} · {self.title}"
