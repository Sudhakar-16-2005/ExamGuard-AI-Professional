from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super administrator"
        AUTHORITY_ADMIN = "authority_admin", "Authority administrator"
        EXAM_OFFICER = "exam_officer", "Examination officer"
        ANALYST = "analyst", "Leak analyst"
        AUDITOR = "auditor", "Auditor"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="examguard_profile",
    )
    authority = models.ForeignKey(
        "authorities.Authority", on_delete=models.SET_NULL, null=True, blank=True
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.ANALYST)
    phone = models.CharField(max_length=24, blank=True)
    is_mfa_enabled = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.user.get_username()} · {self.get_role_display()}"
