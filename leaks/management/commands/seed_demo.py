from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from authorities.models import Authority
from exams.models import Exam, ExamType, Paper, Question
from leaks.models import Source


class Command(BaseCommand):
    help = (
        "Create safe demonstration records. It never creates real monitoring targets."
    )

    def handle(self, *args, **options):
        authority, _ = Authority.objects.get_or_create(
            code="DEMO-AUTH",
            defaults={
                "name": "Demonstration Examination Authority",
                "authority_type": Authority.Type.INSTITUTION,
                "jurisdiction": "Demonstration only",
            },
        )
        exam_type, _ = ExamType.objects.get_or_create(
            code="DEMO-UNI",
            defaults={
                "name": "University Semester Examination",
                "scope": ExamType.Scope.UNIVERSITY,
            },
        )
        start = timezone.now() + timedelta(days=7)
        exam, _ = Exam.objects.get_or_create(
            code="DEMO-SEM-001",
            defaults={
                "authority": authority,
                "exam_type": exam_type,
                "name": "Demonstration Computer Science Semester Exam",
                "academic_year": str(start.year),
                "starts_at": start,
                "ends_at": start + timedelta(hours=3),
                "status": Exam.Status.SCHEDULED,
            },
        )
        paper, _ = Paper.objects.get_or_create(
            exam=exam,
            paper_code="DEMO-CS-101-A",
            set_code="A",
            defaults={
                "subject": "Computer Science",
                "status": Paper.Status.READY,
                "extracted_text": "Explain database normalization and transaction isolation using suitable examples.",
            },
        )
        Question.objects.get_or_create(
            paper=paper,
            number="1",
            defaults={
                "text": "Explain database normalization and transaction isolation using suitable examples.",
                "marks": 10,
            },
        )
        Source.objects.get_or_create(
            name="Manual Demonstration Intake",
            defaults={
                "source_type": Source.Type.MANUAL,
                "access_scope": Source.Scope.OWNED_TEST,
                "authorization_confirmed": True,
                "authorization_note": "Local demonstration data controlled by the project owner.",
            },
        )
        User = get_user_model()
        if not User.objects.filter(username="admin").exists():
            password = "ExamGuard@123"
            User.objects.create_superuser("admin", "admin@example.test", password)
            self.stdout.write(
                self.style.WARNING(
                    f"Demo admin created: admin / {password}. Change it immediately."
                )
            )
        self.stdout.write(self.style.SUCCESS("Demonstration data is ready."))
