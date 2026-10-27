from django.urls import path

from . import views

app_name = "leaks"

urlpatterns = [
    path("telegram/webhook/", views.telegram_webhook, name="telegram-webhook"),
    path("whatsapp/webhook/", views.whatsapp_webhook, name="whatsapp-webhook"),
]
