import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from leaks.models import Source
from leaks.services.ingestion import create_upload


class Command(BaseCommand):
    help = "Read recent messages from configured public or explicitly authorized Telegram sources using MTProto."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            raise CommandError("Set TELEGRAM_API_ID and TELEGRAM_API_HASH first.")
        asyncio.run(self.run_monitor(options["limit"]))

    async def run_monitor(self, limit):
        from asgiref.sync import sync_to_async
        from telethon import TelegramClient

        sources = await sync_to_async(list)(
            Source.objects.filter(
                source_type=Source.Type.TELEGRAM_MTPROTO, is_enabled=True
            )
        )
        client = TelegramClient(
            settings.TELEGRAM_SESSION,
            int(settings.TELEGRAM_API_ID),
            settings.TELEGRAM_API_HASH,
        )
        async with client:
            for source in sources:
                if (
                    source.access_scope != Source.Scope.PUBLIC
                    and not source.authorization_confirmed
                ):
                    self.stderr.write(
                        f"Skipped unauthorized private source: {source.name}"
                    )
                    continue
                try:
                    entity = await client.get_entity(source.endpoint)
                    async for message in client.iter_messages(entity, limit=limit):
                        file_bytes = filename = None
                        if (
                            message.file
                            and (message.file.size or 0) <= settings.MONITOR_MAX_BYTES
                        ):
                            file_bytes = await client.download_media(message, bytes)
                            filename = (
                                getattr(message.file, "name", None)
                                or f"telegram-{message.id}.bin"
                            )
                        await sync_to_async(create_upload)(
                            source=source,
                            external_id=str(message.id),
                            text=message.message or "",
                            content=file_bytes,
                            filename=filename or "telegram.txt",
                            content_type=getattr(
                                message.file, "mime_type", "text/plain"
                            )
                            if message.file
                            else "text/plain",
                            sender_reference=str(message.sender_id or ""),
                            metadata={
                                "date": message.date.isoformat()
                                if message.date
                                else None
                            },
                        )
                    source.last_checked_at = timezone.now()
                    source.last_error = ""
                    await sync_to_async(source.save)(
                        update_fields=("last_checked_at", "last_error")
                    )
                    self.stdout.write(self.style.SUCCESS(f"Checked {source.name}"))
                except Exception as exc:  # noqa: BLE001 - connector failures are isolated per source
                    source.last_checked_at = timezone.now()
                    source.last_error = str(exc)[:2000]
                    await sync_to_async(source.save)(
                        update_fields=("last_checked_at", "last_error")
                    )
                    self.stderr.write(f"{source.name}: {exc}")
