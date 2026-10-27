# ExamGuard AI

**ExamGuard AI** is a professional multi-exam question-paper leak detection and forensics platform for NEET, JEE, state-board public examinations, university semester examinations, and configurable institutional exams.

It uses Django and PostgreSQL, Django Admin as the operations dashboard, PyMuPDF plus PaddleOCR/pytesseract for document text extraction, and scikit-learn TF-IDF with cosine similarity for explainable candidate matching.

> This repository is an engineering reference and demonstration system, not an official examination-authority deployment. Use only public sources and sources for which you have explicit permission.

## Capabilities

- Multi-authority and multi-exam registry
- Protected paper and question corpus with SHA-256 fingerprints
- OCR for scanned PDF and image evidence
- Word + character TF-IDF similarity matching
- Configurable review and critical thresholds per exam
- Pending findings and human-confirmed incident workflow
- Public website, RSS, and approved search/API feed monitoring
- Telegram Bot API webhooks for deliberately connected chats
- Telethon monitoring of public or explicitly authorized channels
- WhatsApp Business Cloud API webhook ingestion
- Manual evidence intake
- Source authorization records and privacy boundaries
- Responsive, branded Django Admin command dashboard
- PostgreSQL, Docker, Gunicorn, and WhiteNoise configuration
- Automated tests for security, validation, matching, and webhooks

## Evidence pipeline

```text
Authorized source -> Upload + hash -> PDF text/OCR -> TF-IDF vectors
-> cosine similarity -> pending Match -> incident candidate -> human confirmation
```

An automated incident candidate is not an official leak determination. A designated reviewer must examine the source, excerpt, file, hash, and score before confirming it.

## Project structure

```text
exam_guard/     Django settings, URLs, WSGI/ASGI, custom AdminSite
accounts/       User roles/profile and password-policy tests
authorities/    Examination authority model and admin
exams/          ExamType, Exam, Paper, Question models and admin
leaks/          Source, Upload, Match, Incident, connectors and commands
templates/      Professional Django Admin templates
static/         Admin dashboard theme
docs/           Architecture, connector setup, and testing guides
```

## Windows setup (PowerShell)

Use Python 3.11 or 3.12. In VS Code, open the extracted `ExamGuard-AI` folder and run:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Install the Tesseract application separately and ensure `tesseract.exe` is on PATH. To use PaddleOCR as well:

```powershell
python -m pip install -r requirements-paddle.txt
```

Install the correct PaddlePaddle CPU/GPU wheel for your computer by following its official installation selector. If PaddleOCR is unavailable, `OCR_ENGINE=auto` safely falls back to Tesseract.

## PostgreSQL setup

Using PostgreSQL's `psql` as an administrator:

```sql
CREATE USER examguard WITH PASSWORD 'choose-a-strong-local-password';
CREATE DATABASE examguard OWNER examguard;
```

Update only your local `.env`:

```text
DATABASE_URL=postgresql://examguard:choose-a-strong-local-password@127.0.0.1:5432/examguard
```

Never commit `.env`.

## Create the database and start

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

Open `http://127.0.0.1:8000/admin/`.

`seed_demo` creates safe sample records and creates a temporary admin only when no `admin` user exists. Change the displayed temporary password immediately. For normal use, prefer the superuser you created yourself.

## Docker start

Docker Compose includes PostgreSQL and Tesseract:

```powershell
docker compose up --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo
```

Then open `http://127.0.0.1:8000/admin/`.

## Admin workflow

1. Add an **Authority**.
2. Add an **Exam type** and **Exam**, including review and critical thresholds.
3. Add a **Paper** and questions, or upload a reference PDF and use the `Extract text and prepare selected papers` Admin action.
4. Add one or more **Sources**. Private/test sources require the authorization checkbox and a written authorization note.
5. Run the appropriate monitor or receive official webhook events.
6. Review **Uploads**, **Matches**, and automatically created incident candidates.
7. Confirm valid findings through the Match Admin action; assign and manage the Incident.

## Monitor commands

```powershell
# One pass over enabled public website/RSS/search-feed records
python manage.py monitor_sources

# One specific web Source
python manage.py monitor_sources --source 3

# Recent posts from configured public/authorized MTProto sources
python manage.py monitor_telegram --limit 20

# Register the Telegram Bot API webhook after setting a public HTTPS SITE_BASE_URL
python manage.py configure_telegram_webhook
```

Use Windows Task Scheduler, cron, or a production job queue to run polling commands periodically. See [docs/CONNECTORS.md](docs/CONNECTORS.md) for the exact permissions and safety model.

## Password policy

Passwords have a minimum length of **8 characters**. Django's similarity, common-password, and numeric-only validators are also enabled. Automated tests cover both 7-character rejection and valid 8-character acceptance.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python manage.py check --deploy
```

## Important limitations

- No responsible system can truthfully promise access to every website.
- Search coverage requires approved/licensed APIs or feeds; scraping arbitrary search pages is not included.
- Telegram private sources require legitimate membership and recorded permission.
- WhatsApp support is limited to official Business webhook traffic delivered to the configured business number.
- Visible and searchable text can be altered; production forensics should add evaluated invisible watermarking and controlled paper variants.
- A real deployment needs malware scanning, encrypted object storage, KMS/HSM, a background queue, immutable audit export, VAPT, legal/privacy review, backups, and disaster recovery.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Connector and permission setup](docs/CONNECTORS.md)
- [Testing guide](docs/TESTING.md)
- [Security policy](SECURITY.md)

Designed and developed by **Sudhakar K**.
