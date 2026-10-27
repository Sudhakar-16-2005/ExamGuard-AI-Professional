import hashlib
import hmac

import requests
from django.conf import settings

from leaks.models import Source

from .ingestion import create_upload


def valid_signature(body: bytes, signature_header: str) -> bool:
    if not settings.WHATSAPP_APP_SECRET or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.WHATSAPP_APP_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header[7:], expected)


def _download_media(media_id: str) -> tuple[bytes, str, str]:
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    graph = f"https://graph.facebook.com/{settings.WHATSAPP_GRAPH_VERSION}"
    metadata = requests.get(f"{graph}/{media_id}", headers=headers, timeout=15)
    metadata.raise_for_status()
    payload = metadata.json()
    response = requests.get(payload["url"], headers=headers, timeout=30)
    response.raise_for_status()
    if len(response.content) > settings.MONITOR_MAX_BYTES:
        raise ValueError("WhatsApp media exceeds configured evidence size limit.")
    mime = payload.get("mime_type", "application/octet-stream")
    extension = mime.split("/")[-1].split("+")[0]
    return response.content, f"whatsapp-{media_id}.{extension}", mime


def ingest_webhook(payload: dict) -> int:
    count = 0
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id")
            source = Source.objects.filter(
                source_type=Source.Type.WHATSAPP,
                endpoint=str(phone_number_id),
                is_enabled=True,
            ).first()
            if not source or not source.authorization_confirmed:
                continue
            for message in value.get("messages", []):
                kind = message.get("type", "")
                text = (message.get("text") or {}).get("body", "")
                media = message.get(kind, {}) if kind in {"image", "document"} else {}
                content = filename = None
                mime = "text/plain"
                if media.get("id"):
                    content, filename, mime = _download_media(media["id"])
                    text = media.get("caption", text)
                create_upload(
                    source=source,
                    external_id=message.get("id", ""),
                    text=text,
                    content=content,
                    filename=filename or "whatsapp.txt",
                    content_type=mime,
                    sender_reference=message.get("from", ""),
                    metadata={
                        "message_type": kind,
                        "timestamp": message.get("timestamp"),
                    },
                )
                count += 1
    return count
