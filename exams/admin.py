from django.contrib import admin, messages

from accounts.admin_mixins import AuthorityScopedAdminMixin

from .models import Exam, ExamType, Paper, Question


class PaperInline(admin.TabularInline):
    model = Paper
    extra = 0
    fields = ("subject", "paper_code", "set_code", "language", "status")
    show_change_link = True


@admin.register(ExamType)
class ExamTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "scope", "is_active")
    list_filter = ("scope", "is_active")
    search_fields = ("code", "name")


@admin.register(Exam)
class ExamAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "exam_type",
        "authority",
        "starts_at",
        "status",
        "paper_count",
    )
    list_filter = (
        "status",
        "exam_type__scope",
        "authority",
        "academic_year",
        "starts_at",
    )
    search_fields = ("code", "name", "authority__name", "authority__code")
    date_hierarchy = "starts_at"
    readonly_fields = ("created_at", "updated_at")
    inlines = (PaperInline,)
    fieldsets = (
        (
            "Identity",
            {"fields": ("authority", "exam_type", "name", "code", "academic_year")},
        ),
        (
            "Schedule and state",
            {"fields": ("starts_at", "ends_at", "status", "languages")},
        ),
        (
            "Leak detection",
            {"fields": ("similarity_threshold", "critical_threshold", "config")},
        ),
        (
            "Audit",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Papers")
    def paper_count(self, obj):
        return obj.papers.count()

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fields = ("number", "text", "marks")


@admin.register(Paper)
class PaperAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    authority_lookup = "exam__authority"
    list_display = (
        "paper_code",
        "subject",
        "exam",
        "language",
        "status",
        "short_hash",
        "updated_at",
    )
    list_filter = ("status", "language", "exam__exam_type__scope", "exam__authority")
    search_fields = (
        "paper_code",
        "set_code",
        "subject",
        "exam__name",
        "exam__code",
        "sha256",
    )
    readonly_fields = ("sha256", "extracted_text", "created_at", "updated_at")
    inlines = (QuestionInline,)
    actions = ("process_selected_papers",)

    @admin.display(description="SHA-256")
    def short_hash(self, obj):
        return f"{obj.sha256[:12]}…" if obj.sha256 else "—"

    @admin.action(description="Extract text and prepare selected papers")
    def process_selected_papers(self, request, queryset):
        from leaks.services.ocr import extract_text_from_path

        processed = 0
        for paper in queryset:
            if not paper.reference_file:
                continue
            paper.status = Paper.Status.PROCESSING
            paper.save(update_fields=("status",))
            paper.extracted_text = extract_text_from_path(paper.reference_file.path)
            paper.sha256 = paper.compute_hash()
            paper.status = (
                Paper.Status.READY if paper.extracted_text else Paper.Status.DRAFT
            )
            paper.save(
                update_fields=("extracted_text", "sha256", "status", "updated_at")
            )
            processed += 1
        self.message_user(request, f"Prepared {processed} paper(s).", messages.SUCCESS)


@admin.register(Question)
class QuestionAdmin(AuthorityScopedAdminMixin, admin.ModelAdmin):
    authority_lookup = "paper__exam__authority"
    list_display = ("paper", "number", "marks", "short_fingerprint")
    list_filter = ("paper__exam__exam_type__scope", "paper__exam", "paper")
    search_fields = ("text", "number", "paper__paper_code", "fingerprint")
    readonly_fields = ("fingerprint", "created_at")

    @admin.display(description="Fingerprint")
    def short_fingerprint(self, obj):
        return f"{obj.fingerprint[:12]}…"
