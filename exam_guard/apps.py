from django.contrib.admin.apps import AdminConfig


class ExamGuardAdminConfig(AdminConfig):
    default_site = "exam_guard.admin.ExamGuardAdminSite"
