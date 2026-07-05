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

## v2 milestone

Features deferred from v1 are tracked under the [v2 milestone](https://github.com/donolu/provena/milestone/1). This includes post-launch enhancements that are well-understood but not required at launch, and items that are blocked on another issue being completed first.

## Won't fix (accepted limitations)

The following are known limitations that will not be addressed in the near term:

| Item | Reason |
|---|---|
| SMS 2FA | WhatsApp/SMS 2FA is optional per BRD. TOTP authenticator app covers the requirement for privileged roles. |
| Multi-currency | All prices stored in GBP pence. Stripe supports multi-currency but the platform is UK-market only at launch. |
| Mobile apps | Out of scope. The Next.js frontend is responsive. |
| Real-time order tracking | Deferred to v2 (#42). The order detail page polls for updates in v1. |
| GDPR data portability self-service | Deferred to v2 (#41). Article 20 right acknowledged in COMPLIANCE.md. Export currently requires an admin to run a manual extract. |
