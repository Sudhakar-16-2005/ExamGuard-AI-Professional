from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from authorities.models import Authority
from exams.models import Exam, ExamType, Paper, Question
from leaks.models import Incident, Match, Source, Upload
from leaks.services.ingestion import create_upload


class LeakPipelineTests(TestCase):
    def setUp(self):
        authority = Authority.objects.create(
            name="Test Authority",
            code="TEST",
            authority_type=Authority.Type.INSTITUTION,
        )
        exam_type = ExamType.objects.create(
            name="University", code="TEST-UNI", scope=ExamType.Scope.UNIVERSITY
        )
        start = timezone.now() + timedelta(days=1)
        self.exam = Exam.objects.create(
            authority=authority,
            exam_type=exam_type,
            name="Test Exam",
            code="TEST-EXAM",
            academic_year="2026",
            starts_at=start,
            ends_at=start + timedelta(hours=3),
            status=Exam.Status.SCHEDULED,
            similarity_threshold=0.50,
            critical_threshold=0.75,
        )
        self.paper = Paper.objects.create(
            exam=self.exam,
            subject="Databases",
            paper_code="DB-101",
            set_code="A",
            status=Paper.Status.READY,
        )
        self.question = Question.objects.create(
            paper=self.paper,
            number="1",
            text="Explain database normalization and transaction isolation with examples.",
        )
        self.source = Source.objects.create(
            name="Owned test intake",
            source_type=Source.Type.MANUAL,
            access_scope=Source.Scope.OWNED_TEST,
            authorization_confirmed=True,
            authorization_note="Controlled automated test.",
        )

    def test_exact_question_creates_match_and_incident_candidate(self):
        upload = create_upload(
            source=self.source,
            external_id="test-1",
            text="Explain database normalization and transaction isolation with examples.",
            content_type="text/plain",
        )
        match = Match.objects.get(upload=upload)
        self.assertGreaterEqual(match.similarity_score, 0.75)
        self.assertEqual(match.status, Match.Status.PENDING)
        incident = Incident.objects.get(match=match)
        self.assertEqual(incident.status, Incident.Status.NEW)
        self.assertIsNone(incident.confirmed_by)

    def test_duplicate_external_item_is_idempotent(self):
        first = create_upload(
            source=self.source, external_id="same", text="harmless short message"
        )
        second = create_upload(
            source=self.source, external_id="same", text="different text"
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            Upload.objects.filter(source=self.source, external_id="same").count(), 1
        )

    def test_private_source_requires_recorded_permission(self):
        source = Source(
            name="Unapproved private source",
            source_type=Source.Type.TELEGRAM_BOT,
            access_scope=Source.Scope.AUTHORIZED_PRIVATE,
            endpoint="-100123",
        )
        with self.assertRaises(ValidationError):
            source.full_clean()


class WebhookSecurityTests(TestCase):
    @override_settings(TELEGRAM_WEBHOOK_SECRET="expected-secret")
    def test_telegram_rejects_wrong_secret(self):
        response = self.client.post(
            "/integrations/telegram/webhook/",
            data="{}",
            content_type="application/json",
            HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_APP_SECRET="test-app-secret")
    def test_whatsapp_rejects_missing_signature(self):
        response = self.client.post(
            "/integrations/whatsapp/webhook/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_VERIFY_TOKEN="verify-me")
    def test_whatsapp_verification_challenge(self):
        response = self.client.get(
            "/integrations/whatsapp/webhook/?hub.verify_token=verify-me&hub.challenge=12345"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"12345")
