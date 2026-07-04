# Backlog

The backlog is tracked as GitHub Issues: https://github.com/donolu/provena/issues

## Issue labels

| Label | Meaning |
|---|---|
| `enhancement` | New feature or improvement |
| `infrastructure` | Deployment, scaling, observability |
| `chore` | Tooling, dependencies, configuration |
| `tech-debt` | Code quality and architectural improvements |
| `bug` | Something not working as expected |

## Won't fix (accepted limitations)

The following are known limitations that will not be addressed in the near term:

| Item | Reason |
|---|---|
| SMS 2FA | WhatsApp/SMS 2FA is optional per BRD. TOTP authenticator app covers the requirement for privileged roles. |
| Multi-currency | All prices stored in GBP pence. Stripe supports multi-currency but the platform is UK-market only at launch. |
| Mobile apps | Out of scope. The Next.js frontend is responsive. |
| Real-time order tracking | WebSocket push not implemented. The order detail page polls for updates. |
| GDPR data portability self-service | Article 20 right acknowledged in COMPLIANCE.md. Export currently requires an admin to run a manual extract. |
