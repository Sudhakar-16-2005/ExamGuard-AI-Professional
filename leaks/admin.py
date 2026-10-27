from django.contrib import admin, messages
from django.utils import timezone

from accounts.admin_mixins import AuthorityScopedAdminMixin

from .models import Incident, Match, Source, Upload


@admin.register(Source)
class SourceAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "access_scope",
        "authority",
        "is_enabled",
        "authorization_confirmed",
        "last_checked_at",
    )
    list_filter = (
        "source_type",
        "access_scope",
        "is_enabled",
        "authorization_confirmed",
        "authority",
    )
    search_fields = ("name", "endpoint", "authority__name")
    readonly_fields = (
        "authorized_at",
        "last_checked_at",
        "last_error",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Source",
            {"fields": ("name", "source_type", "endpoint", "authority", "is_enabled")},
        ),
        (
            "Permission boundary",
            {
                "fields": (
                    "access_scope",
                    "authorization_confirmed",
                    "authorization_note",
                    "authorized_by",
                    "authorized_at",
                    "terms_note",
                )
            },
        ),
        ("Monitoring", {"fields": ("config", "last_checked_at", "last_error")}),
        ("Audit", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    def save_model(self, request, obj, form, change):
        if obj.authorization_confirmed and not obj.authorized_by_id:
            obj.authorized_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Upload)
class UploadAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    authority_lookup = "source__authority"
    list_display = (
        "id",
        "source",
        "content_type",
        "status",
        "short_hash",
        "captured_at",
        "match_count",
    )
    list_filter = ("status", "source__source_type", "source", "captured_at")
    search_fields = (
        "external_id",
        "original_url",
        "sha256",
        "raw_text",
        "extracted_text",
    )
    readonly_fields = ("sha256", "extracted_text", "processed_at", "created_at")
    date_hierarchy = "captured_at"
    actions = ("process_uploads",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if (
            not change
            or "evidence_file" in form.changed_data
            or "raw_text" in form.changed_data
        ):
            from .services.ingestion import process_upload

            process_upload(obj)

    @admin.display(description="SHA-256")
    def short_hash(self, obj):
        return f"{obj.sha256[:12]}…" if obj.sha256 else "—"

    @admin.display(description="Matches")
    def match_count(self, obj):
        return obj.matches.count()

    @admin.action(description="Run OCR and similarity analysis")
    def process_uploads(self, request, queryset):
        from .services.ingestion import process_upload

        success = 0
        for upload in queryset:
            try:
                process_upload(upload)
                success += 1
            except Exception as exc:  # noqa: BLE001 - one failed evidence item must not stop the batch
                self.message_user(request, f"Upload {upload.pk}: {exc}", messages.ERROR)
        self.message_user(request, f"Processed {success} upload(s).", messages.SUCCESS)


@admin.register(Match)
class MatchAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    authority_lookup = "paper__exam__authority"
    list_display = (
        "upload",
        "paper",
        "question",
        "score_percent",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "paper__exam__exam_type__scope",
        "paper__exam",
        "paper",
        "created_at",
    )
    search_fields = (
        "paper__paper_code",
        "paper__subject",
        "upload__sha256",
        "matched_excerpt",
    )
    readonly_fields = ("algorithm", "similarity_score", "evidence", "created_at")
    actions = ("confirm_matches", "mark_false_positive")

    @admin.display(description="Score", ordering="similarity_score")
    def score_percent(self, obj):
        return f"{obj.similarity_score:.1%}"

    @admin.action(description="Confirm selected matches")
    def confirm_matches(self, request, queryset):
        for match in queryset:
            match.status = Match.Status.CONFIRMED
            match.reviewed_by = request.user
            match.reviewed_at = timezone.now()
            match.save(update_fields=("status", "reviewed_by", "reviewed_at"))
            incident = getattr(match, "incident", None)
            if incident:
                incident.confirmed_by = request.user
                incident.confirmed_at = timezone.now()
                incident.status = Incident.Status.INVESTIGATING
                incident.save(
                    update_fields=(
                        "confirmed_by",
                        "confirmed_at",
                        "status",
                        "updated_at",
                    )
                )
        self.message_user(
            request,
            "Selected findings were confirmed and moved to investigation.",
            messages.SUCCESS,
        )

    @admin.action(description="Mark selected matches as false positives")
    def mark_false_positive(self, request, queryset):
        queryset.update(
            status=Match.Status.FALSE_POSITIVE,
            reviewed_by=request.user,
            reviewed_at=timezone.now(),
        )


@admin.register(Incident)
class IncidentAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    authority_lookup = "exam__authority"
    list_display = (
        "incident_code",
        "title",
        "exam",
        "severity",
        "status",
        "source_name",
        "score",
        "detected_at",
        "assigned_to",
    )
    list_filter = (
        "severity",
        "status",
        "exam__exam_type__scope",
        "exam__authority",
        "detected_at",
        "confirmed_at",
    )
    search_fields = (
        "incident_code",
        "title",
        "description",
        "exam__code",
        "exam__name",
        "match__upload__original_url",
        "match__upload__sha256",
    )
    readonly_fields = ("incident_code", "detected_at", "created_at", "updated_at")
    date_hierarchy = "detected_at"
    list_select_related = ("exam", "match__upload__source", "assigned_to")
    fieldsets = (
        (
            "Incident",
            {"fields": ("incident_code", "title", "exam", "severity", "status")},
        ),
        ("Finding", {"fields": ("match", "description", "evidence")}),
        (
            "Response",
            {
                "fields": (
                    "assigned_to",
                    "confirmed_by",
                    "confirmed_at",
                    "response_actions",
                    "resolved_at",
                )
            },
        ),
        (
            "Timeline",
            {
                "fields": ("detected_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Source")
    def source_name(self, obj):
        return obj.match.upload.source.name if obj.match_id else "Manual"

    @admin.display(description="Score", ordering="match__similarity_score")
    def score(self, obj):
        return f"{obj.match.similarity_score:.1%}" if obj.match_id else "—"
