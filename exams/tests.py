from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from authorities.models import Authority

from .models import Exam, ExamType


class ExamValidationTests(TestCase):
    def setUp(self):
        self.authority = Authority.objects.create(
            name="Test Authority", code="TA", authority_type=Authority.Type.INSTITUTION
        )
        self.exam_type = ExamType.objects.create(
            name="University", code="UNI", scope=ExamType.Scope.UNIVERSITY
        )

    def test_exam_end_must_follow_start(self):
        now = timezone.now()
        exam = Exam(
            authority=self.authority,
            exam_type=self.exam_type,
            name="Invalid schedule",
            code="INVALID",
            academic_year="2026",
            starts_at=now,
            ends_at=now - timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            exam.full_clean()

    def test_critical_threshold_cannot_be_lower(self):
        now = timezone.now()
        exam = Exam(
            authority=self.authority,
            exam_type=self.exam_type,
            name="Invalid threshold",
            code="THRESHOLD",
            academic_year="2026",
            starts_at=now,
            ends_at=now + timedelta(hours=2),
            similarity_threshold=0.8,
            critical_threshold=0.7,
        )
        with self.assertRaises(ValidationError):
            exam.full_clean()
