import hmac

import requests
from django.conf import settings

from leaks.models import Source

from .ingestion import create_upload


def _configured_source(source_type: str, chat_id) -> Source | None:
    return Source.objects.filter(
        source_type=source_type, endpoint=str(chat_id), is_enabled=True
    ).first()


def _download_bot_file(file_id: str) -> tuple[bytes, str]:
    token = settings.TELEGRAM_BOT_TOKEN
    info = requests.get(
        f"https://api.telegram.org/bot{token}/getFile",
        params={"file_id": file_id},
        timeout=15,
    ).json()
    if not info.get("ok"):
        raise ValueError("Telegram did not return the requested file.")
    file_path = info["result"]["file_path"]
    response = requests.get(
        f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=30
    )
    response.raise_for_status()
    if len(response.content) > settings.MONITOR_MAX_BYTES:
        raise ValueError("Telegram file exceeds configured evidence size limit.")
    return response.content, file_path.rsplit("/", 1)[-1]


def ingest_bot_update(update: dict):
    message = (
        update.get("channel_post")
        or update.get("edited_channel_post")
        or update.get("message")
    )
    if not message:
        return None
    chat = message.get("chat", {})
    source = _configured_source(Source.Type.TELEGRAM_BOT, chat.get("id"))
    if not source:
        return None
    if (
        source.access_scope != Source.Scope.PUBLIC
        and not source.authorization_confirmed
    ):
        raise PermissionError("This Telegram source has no recorded authorization.")
    text = message.get("text") or message.get("caption") or ""
    document = message.get("document")
    photos = message.get("photo") or []
    content, filename, content_type = None, "", "text/plain"
    if document:
        content, filename = _download_bot_file(document["file_id"])
        content_type = document.get("mime_type", "application/octet-stream")
    elif photos:
        content, filename = _download_bot_file(photos[-1]["file_id"])
        content_type = "image/jpeg"
    return create_upload(
        source=source,
        external_id=str(message.get("message_id", "")),
        text=text,
        content=content,
        filename=filename or "telegram.txt",
        content_type=content_type,
        original_url=f"https://t.me/{chat.get('username')}/{message.get('message_id')}"
        if chat.get("username")
        else "",
        sender_reference=str((message.get("from") or {}).get("id", "")),
        metadata={
            "chat_type": chat.get("type"),
            "chat_title": chat.get("title", ""),
            "edited": "edited_channel_post" in update,
        },
    )


def valid_webhook_secret(received: str) -> bool:
    expected = settings.TELEGRAM_WEBHOOK_SECRET
    return bool(expected and hmac.compare_digest(received or "", expected))
