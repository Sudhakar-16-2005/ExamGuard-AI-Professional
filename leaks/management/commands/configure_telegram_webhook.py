import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Register the ExamGuard AI Telegram Bot API webhook."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("Set TELEGRAM_BOT_TOKEN first.")
        if not settings.TELEGRAM_WEBHOOK_SECRET:
            raise CommandError("Set TELEGRAM_WEBHOOK_SECRET to a random value first.")
        url = f"{settings.SITE_BASE_URL}/integrations/telegram/webhook/"
        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setWebhook",
            json={
                "url": url,
                "secret_token": settings.TELEGRAM_WEBHOOK_SECRET,
                "allowed_updates": ["message", "channel_post", "edited_channel_post"],
                "drop_pending_updates": False,
            },
            timeout=20,
        )
        payload = response.json()
        if not response.ok or not payload.get("ok"):
            raise CommandError(
                payload.get("description", "Telegram webhook configuration failed.")
            )
        self.stdout.write(self.style.SUCCESS(f"Telegram webhook configured: {url}"))
