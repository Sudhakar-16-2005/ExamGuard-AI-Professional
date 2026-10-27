# Testing Guide

Run the automated suite:

```powershell
python -m pytest -q
```

The tests verify:

- passwords shorter than 8 characters are rejected;
- a valid 8-character password passes the minimum-length validator;
- Admin requires authentication;
- exam schedules and detection thresholds are validated;
- private sources cannot pass validation without recorded permission;
- duplicate external items are idempotent;
- exact protected-question text produces a high similarity Match and incident candidate;
- incidents remain pending human confirmation;
- Telegram rejects an invalid webhook secret;
- WhatsApp rejects an invalid signature and supports its verification challenge.

Manual workflow:

1. Run migrations and `python manage.py seed_demo`.
2. Sign in to `/admin/` with the temporary demonstration account and change its password immediately.
3. Inspect the demonstration Authority, Exam, Paper, Question, and manual Source.
4. Add an Upload under **Leak intelligence**, paste the demonstration question into `raw_text`, and save.
5. Open Matches and verify that the score, paper, question, source, fingerprint, and pending-review state are present.
6. Open Incidents and verify that the candidate is not yet confirmed.
7. Use the **Confirm selected matches** action as an authorized reviewer and verify that the incident moves to investigation.
