import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from leaks.models import Incident, Match, Source, Upload

from .ocr import extract_text_from_path
from .similarity import excerpt, find_candidate_matches


def create_upload(
    *,
    source: Source,
    external_id: str = "",
    text: str = "",
    content: bytes | None = None,
    filename: str = "evidence.bin",
    content_type: str = "",
    original_url: str = "",
    sender_reference: str = "",
    metadata: dict | None = None,
) -> Upload:
    if external_id:
        existing = Upload.objects.filter(source=source, external_id=external_id).first()
        if existing:
            return existing
    upload = Upload(
        source=source,
        external_id=external_id,
        raw_text=text or "",
        content_type=content_type,
        original_url=original_url,
        sender_reference=sender_reference,
        metadata=metadata or {},
    )
    if content:
        upload.sha256 = hashlib.sha256(content).hexdigest()
        upload.evidence_file.save(Path(filename).name, ContentFile(content), save=False)
    elif text:
        upload.sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    upload.save()
    process_upload(upload)
    return upload


@transaction.atomic
def process_upload(upload: Upload) -> Upload:
    upload.status = Upload.Status.PROCESSING
    upload.error = ""
    upload.save(update_fields=("status", "error"))
    try:
        if upload.evidence_file and not upload.sha256:
            hasher = hashlib.sha256()
            upload.evidence_file.open("rb")
            try:
                for chunk in upload.evidence_file.chunks():
                    hasher.update(chunk)
            finally:
                upload.evidence_file.close()
            upload.sha256 = hasher.hexdigest()
        extracted = upload.raw_text
        if upload.evidence_file:
            file_text = extract_text_from_path(upload.evidence_file.path)
            extracted = f"{extracted}\n{file_text}".strip()
        upload.extracted_text = extracted
        upload.processed_at = timezone.now()
        upload.status = Upload.Status.PROCESSED
        upload.save(
            update_fields=("sha256", "extracted_text", "processed_at", "status")
        )

        for candidate in find_candidate_matches(extracted):
            paper = candidate["paper"]
            score = candidate["score"]
            threshold = (
                paper.exam.similarity_threshold or settings.MATCH_REVIEW_THRESHOLD
            )
            if score < threshold:
                continue
            match, _ = Match.objects.update_or_create(
                upload=upload,
                paper=paper,
                question=candidate["question"],
                defaults={
                    "similarity_score": score,
                    "matched_excerpt": excerpt(extracted),
                    "evidence": {
                        "threshold": threshold,
                        "source_type": upload.source.source_type,
                    },
                },
            )
            if score >= paper.exam.critical_threshold:
                Incident.objects.get_or_create(
                    match=match,
                    defaults={
                        "exam": paper.exam,
                        "title": f"Possible {paper.exam.code} paper exposure",
                        "description": "Automated high-similarity finding. Human confirmation is required before official classification.",
                        "severity": Incident.Severity.CRITICAL,
                        "evidence": {
                            "upload_id": upload.pk,
                            "sha256": upload.sha256,
                            "score": score,
                        },
                    },
                )
        return upload
    except Exception as exc:
        upload.status = Upload.Status.FAILED
        upload.error = str(exc)[:2000]
        upload.processed_at = timezone.now()
        upload.save(update_fields=("status", "error", "processed_at"))
        raise
