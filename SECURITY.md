# Security Policy

ExamGuard AI is a professional reference implementation for authorized examination-security teams. Do not load live question papers, personal data, credentials, or operational evidence into an unapproved development or demonstration environment.

## Non-negotiable monitoring boundary

- Public web sources may be monitored only when their terms, robots policy, applicable law, and the authority's policy permit it.
- A Telegram bot may process only chats where it has been deliberately added. Private sources require a recorded authorization in the `Source` record.
- An MTProto account may join public channels or private channels/groups to which that account has been legitimately invited and authorized. The code contains no discovery or access-bypass mechanism.
- WhatsApp ingestion uses the official Business webhook for messages delivered to the configured business number. It does not read personal chats or unrelated groups.
- Do not use stolen sessions, scraped credentials, invitation harvesting, account automation, or privacy-control bypasses.
- Automated similarity findings remain unconfirmed until an authorized officer reviews them.

## Production controls still required

- Independent security architecture review and penetration testing
- Approved cloud tenancy, data residency, private object storage, encryption with KMS/HSM, and key rotation
- Least-privilege database/service identities and MFA for administrators
- Central secrets management; never commit `.env` or Telegram session files
- Immutable audit export, evidence retention schedules, legal holds, access reviews, backups, and disaster recovery
- Rate limits, background job isolation, alerting, malware scanning, and document sandboxing
- Privacy and legal review for every monitored source and retained identifier

Report vulnerabilities privately to the project owner. Do not publish exploit details before a fix is available.
