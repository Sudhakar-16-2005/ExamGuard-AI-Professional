
import logging
from django.contrib.admin import AdminSite

logger = logging.getLogger(__name__)


class ExamGuardAdminSite(AdminSite):
    site_header = "ExamGuard AI Operations"
    site_title = "ExamGuard AI"
    index_title = "Leak Intelligence & Incident Command"

    def each_context(self, request):
        context = super().each_context(request)

        if request.user.is_authenticated:
            try:
                from exams.models import Exam, Paper
                from leaks.models import Incident, Match, Source, Upload

                context["examguard_metrics"] = {
                    "active_exams": Exam.objects.filter(
                        status__in=["scheduled", "active"]
                    ).count(),
                    "protected_papers": Paper.objects.filter(
                        status="ready"
                    ).count(),
                    "enabled_sources": Source.objects.filter(
                        is_enabled=True
                    ).count(),
                    "pending_matches": Match.objects.filter(
                        status="pending"
                    ).count(),
                    "open_incidents": Incident.objects.exclude(
                        status__in=["resolved", "closed"]
                    ).count(),
                    "total_uploads": Upload.objects.count(),
                }

            except Exception:
                logger.exception("ExamGuard Admin metrics failed")
                context["examguard_metrics"] = {}

        return context
