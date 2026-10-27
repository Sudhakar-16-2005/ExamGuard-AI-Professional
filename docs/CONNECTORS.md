# Authorized Monitoring Setup

## Public websites, feeds, and search providers

1. In Admin, open **Leak intelligence → Sources → Add**.
2. Select `Public website`, `RSS/Atom feed`, or `Search/API feed`.
3. Use a specific public HTTPS endpoint and keep access scope set to `Publicly accessible`.
4. Record the terms/permission basis. Use the JSON config for non-secret options such as `{\"keywords\": [\"question paper\", \"answer key\"], \"interval_minutes\": 15}`.
5. Run `python manage.py monitor_sources` once, then schedule it with Task Scheduler, cron, or a production worker.

Add multiple source records for important pages and feeds. For broad coverage, connect a licensed search or threat-intelligence provider that permits automated use; do not scrape search-engine result pages in violation of provider terms.

## Telegram Bot API

1. Create a bot with BotFather and store its token only in `.env`.
2. Add the bot to each public channel or authority-controlled private test channel. For channel posts, make it an administrator with only the minimum rights needed to receive posts; it does not need permission to delete users or content.
3. For a controlled group where every message must be evaluated, use BotFather `/setprivacy` to disable privacy mode. Keep privacy mode enabled where command-only visibility is sufficient.
4. Create a `Telegram Bot API` Source. Set `endpoint` to the exact numeric chat ID. For a private/test source, mark authorization confirmed and document who authorized it.
5. Configure `TELEGRAM_BOT_TOKEN`, a random `TELEGRAM_WEBHOOK_SECRET`, and public HTTPS `SITE_BASE_URL`.
6. Run `python manage.py configure_telegram_webhook`.

Telegram sends `message`, `channel_post`, and `edited_channel_post` updates. ExamGuard verifies Telegram's webhook secret, checks the chat against enabled Source records, downloads permitted document/image evidence within the size limit, and starts analysis.

## Telegram MTProto with Telethon

1. Create a Telegram API application for an account owned/approved by the examination authority.
2. Put `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` in `.env`.
3. Add Source records of type `Telegram public/authorized client`. Public usernames such as `@channel_name` may be used. Private sources must already be accessible to the account and must have recorded permission.
4. Run `python manage.py monitor_telegram --limit 20`. The first run performs Telegram's normal interactive authorization and creates a local session file.
5. Keep the session file secret and out of Git. Schedule later runs under a protected service identity.

The command never attempts to discover or enter inaccessible private groups.

## WhatsApp Business Cloud API

1. Use an approved Meta app and WhatsApp Business number controlled by the authority.
2. Configure the callback URL as `<SITE_BASE_URL>/integrations/whatsapp/webhook/` and subscribe to message webhooks.
3. Set `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`, and `WHATSAPP_ACCESS_TOKEN` in `.env`.
4. Add an enabled `WhatsApp Business webhook` Source whose endpoint is the exact business `phone_number_id`. Mark authorization confirmed and describe the approved use.
5. Send test text, image, or PDF messages to that business number.

ExamGuard validates the `X-Hub-Signature-256` HMAC before accepting the payload. It can process content delivered to that business account; it cannot inspect private WhatsApp chats or arbitrary groups.

## Permissions summary

| Integration | Required permission | Not required / prohibited |
|---|---|---|
| Public web | Public access plus permitted automated retrieval | Authentication bypass or private-network probing |
| Telegram bot | Bot deliberately added; channel admin for channel posts; privacy disabled only for authorized full-group monitoring | Joining or reading groups where bot was not added |
| Telethon | Legitimate account membership and documented permission for private sources | Stolen sessions, invitation harvesting, privacy bypass |
| WhatsApp | Authority-owned Business app/number, webhook subscription, valid access token | Personal-account scraping or arbitrary group access |

## Official references

- Django password validation: https://docs.djangoproject.com/en/stable/topics/auth/passwords/
- Telegram Bot API: https://core.telegram.org/bots/api
- Telethon chats and public channels: https://docs.telethon.dev/en/stable/examples/chats-and-channels.html
- Meta WhatsApp Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api/
