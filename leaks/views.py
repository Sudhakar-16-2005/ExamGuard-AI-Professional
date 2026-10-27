import json

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services.telegram_monitor import ingest_bot_update, valid_webhook_secret
from .services.whatsapp_monitor import ingest_webhook, valid_signature


@csrf_exempt
@require_POST
def telegram_webhook(request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not valid_webhook_secret(secret):
        return HttpResponseForbidden("Invalid webhook secret")
    try:
        upload = ingest_bot_update(json.loads(request.body))
        return JsonResponse({"ok": True, "accepted": bool(upload)})
    except (ValueError, PermissionError, json.JSONDecodeError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)


@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        if request.GET.get("hub.verify_token") == settings.WHATSAPP_VERIFY_TOKEN:
            return HttpResponse(request.GET.get("hub.challenge", ""))
        return HttpResponseForbidden("Invalid verification token")
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    if not valid_signature(
        request.body, request.headers.get("X-Hub-Signature-256", "")
    ):
        return HttpResponseForbidden("Invalid webhook signature")
    try:
        count = ingest_webhook(json.loads(request.body))
        return JsonResponse({"ok": True, "accepted": count})
    except (ValueError, PermissionError, json.JSONDecodeError) as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)
