from django.db import models


class Authority(models.Model):
    class Type(models.TextChoices):
        NATIONAL = "national", "National examination authority"
        STATE_BOARD = "state_board", "State board"
        UNIVERSITY = "university", "University"
        INSTITUTION = "institution", "Institution"

    name = models.CharField(max_length=180)
    code = models.CharField(max_length=30, unique=True)
    authority_type = models.CharField(max_length=24, choices=Type.choices)
    jurisdiction = models.CharField(max_length=180, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=24, blank=True)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(
        default=dict, blank=True, help_text="Non-secret authority-specific settings."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Authorities"
        ordering = ("name",)

    def __str__(self):
        return f"{self.code} · {self.name}"
