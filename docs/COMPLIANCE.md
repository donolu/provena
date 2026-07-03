# Compliance and Security

**Product:** Provena
**Version:** 1.0
**Frameworks:** PCI DSS, UK GDPR, OWASP Top 10, WCAG 2.1

---

## 1. PCI DSS

### Scope and Compliance Level

Provena uses Stripe for all payment processing. Card data is entered directly into Stripe-hosted fields (Stripe Elements or Stripe Checkout) and never transmitted to or stored on Provena servers.

This means Provena qualifies for **SAQ-A** (Self-Assessment Questionnaire A), the lightest PCI DSS compliance tier. SAQ-A applies to merchants who fully outsource card processing to a PCI-compliant third party.

### Controls Required Under SAQ-A

| Control | Implementation |
|---|---|
| Do not store cardholder data | Stripe handles all card data; Provena stores only `stripe_payment_intent_id` and last-four digits (returned by Stripe, not entered by user) |
| HTTPS on all pages where cardholder data is referenced | Cloudflare enforces HTTPS; HSTS preload enabled |
| Stripe webhook signature verification | `stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)` on every webhook; reject events that fail verification |
| Access controls on admin and dashboard | Role-based access control; TOTP 2FA mandatory for Admin accounts |
| Annual self-assessment | Complete SAQ-A annually via Stripe Dashboard or independently |

### What Provena Must Never Do

- Never log, store, or transmit raw card numbers, CVV, or full track data
- Never build a custom card input form that submits card data to Provena's own server
- Never disable Stripe webhook signature verification

### Stripe Connect (Supplier Payouts)

Supplier payouts use Stripe Connect (platform model). Each supplier completes Stripe's own onboarding (identity verification, bank account). Provena stores `stripe_account_id` per supplier and transfers funds after order delivery.

Commission is deducted at transfer time via Stripe's `application_fee_amount` parameter. Provena never holds funds beyond the standard Stripe payout cycle.

---

## 2. UK GDPR

### Lawful Basis for Processing

| Data | Lawful Basis |
|---|---|
| Account registration data | Contract (necessary to provide the service) |
| Order and payment data | Contract |
| Marketing emails | Consent (opt-in checkbox at registration; withdrawable at any time) |
| Analytics (aggregated, anonymised) | Legitimate interest |
| KYC documents (suppliers) | Legal obligation |

### Data Subject Rights

| Right | Implementation |
|---|---|
| Right of access | User can download their data from account settings; Admin can export on request |
| Right to erasure | Account deletion anonymises PII; order records retained for 7 years (legal/tax obligation) |
| Right to rectification | User can update profile data; email change requires re-verification |
| Right to data portability | Data export returns JSON; available in account settings |
| Right to object | Marketing emails include one-click unsubscribe; analytics tracking can be declined |

### Data Retention Policy

| Category | Retention Period | Reason |
|---|---|---|
| Active user accounts | Indefinite while account is active | Contract performance |
| Inactive user accounts | 3 years after last login, then anonymised | Legitimate interest |
| Order records | 7 years from order date | UK tax law (HMRC) |
| Payment records | 7 years | UK tax law |
| KYC documents | 5 years after supplier offboarding | AML regulations |
| Server logs | 90 days | Security investigation window |
| Audit logs (admin actions) | 3 years | Accountability |
| Abandoned cart data | 48 hours | No further purpose |

### Cookie and Tracking Policy

Provena uses a cookie consent banner on first visit. No non-essential cookies are set until consent is given.

| Cookie | Type | Purpose | Consent Required |
|---|---|---|---|
| `session` | Strictly necessary | Django session | No |
| `csrftoken` | Strictly necessary | CSRF protection | No |
| `auth_token` | Strictly necessary | JWT storage (httpOnly) | No |
| `plausible_*` | Analytics | Privacy-first analytics (no PII) | Yes |
| `stripe_*` | Functional | Stripe fraud detection | Yes (at checkout) |

**Analytics approach:** Use Plausible Analytics (privacy-first, no IP storage, no cross-site tracking) or PostHog (self-hosted). Google Analytics is not used. No third-party advertising pixels.

### Personalisation and Tracking

Personalised product recommendations are generated from the user's own purchase and browse history stored in Provena's own database. This does not involve any third-party data sharing. Users can disable personalisation in account settings.

### Data Breach Response

1. Identify scope and contain the breach within 1 hour of detection
2. Assess whether personal data is affected
3. If personal data is affected and the breach is likely to result in risk to individuals: notify ICO within 72 hours
4. If high risk to individuals: notify affected users directly without undue delay
5. Document the breach, investigation, and actions taken

---

## 3. OWASP Top 10

### A01: Broken Access Control

- Object-level permissions enforced in DRF: every ViewSet checks `request.user` owns or is authorised to access the requested object
- Admin-only endpoints decorated with `IsAdminUser`
- Supplier-only endpoints check `request.user.supplier` exists and is approved
- Horizontal privilege escalation (accessing another user's orders) prevented by queryset filtering: `Order.objects.filter(buyer=request.user)`

### A02: Cryptographic Failures

- HTTPS enforced everywhere; HTTP redirected to HTTPS by Cloudflare and Django's `SECURE_SSL_REDIRECT`
- HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- Passwords hashed with bcrypt (Django's `PBKDF2PasswordHasher` upgraded to `BCryptSHA256PasswordHasher`)
- JWT signed with HS256; `SECRET_KEY` rotated annually
- TLS 1.2 minimum; TLS 1.3 preferred; weak cipher suites disabled at Cloudflare

### A03: Injection

- All database queries use the Django ORM (parameterised queries); raw SQL is forbidden in application code except in schema migrations
- User input never interpolated into query strings
- File upload filenames sanitised before storage; files stored on S3, never served by the application server
- DRF serialisers validate and coerce all input before it reaches the database layer

### A04: Insecure Design

- Threat model reviewed before each major feature launch
- Failed login attempts rate-limited and logged; brute-force lockout after 5 attempts
- Stripe webhook endpoint does not expose order or user data in error responses
- Password reset tokens are single-use, expire in 1 hour, and are invalidated on use

### A05: Security Misconfiguration

Django production settings enforce:

```python
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

Docker images built from minimal base (`python:3.12-slim`); no development tools in production images.

### A06: Vulnerable and Outdated Components

- Python dependencies pinned in `pyproject.toml` with upper bounds
- Dependabot enabled on both repos; patches applied within 7 days for HIGH/CRITICAL CVEs
- `safety check` runs in CI on every push
- Docker base images rebuilt weekly via GitHub Actions schedule

### A07: Identification and Authentication Failures

- TOTP 2FA mandatory for Admin and Supplier roles
- JWT access token TTL: 15 minutes
- Refresh token rotation: each use issues a new refresh token and invalidates the old one
- Refresh token stored in httpOnly cookie; access token in memory only (not localStorage)
- Account lockout: 5 failed attempts triggers 30-minute lockout; Admin can unlock manually
- Password reset: token delivered by email; single-use; 1-hour TTL

### A08: Software and Data Integrity Failures

- All GitHub Actions pinned to specific SHA (not just tag) for third-party actions
- `pip install` uses `--require-hashes` in production Docker builds
- Stripe webhooks: signature verified on every event
- Database backups encrypted and stored separately from primary data

### A09: Security Logging and Monitoring Failures

- Structured JSON logging to stdout; collected by log aggregator (Loki or Papertrail)
- Every request logged: timestamp, method, path, status code, user_id (if authenticated), request_id
- Security events logged at WARN or above: failed logins, permission denials, webhook signature failures
- Audit log table: every Admin action recorded with actor, action, target, timestamp, before/after state
- Sentry captures all unhandled exceptions with stack trace and request context
- Alert on: 5xx rate above 1% for 5 minutes; Celery queue depth above 1,000; DB connection pool exhausted

### A10: Server-Side Request Forgery

- No features require the Django server to fetch user-supplied URLs
- Outbound HTTP calls (Stripe, SendGrid, S3) use explicit URL construction, never user input
- If webhook or integration URLs are ever stored, they are validated against an allowlist

---

## 4. Penetration Testing

### Automated (in CI)

| Tool | Type | When |
|---|---|---|
| Bandit | SAST (Python) | Every push |
| Safety | Dependency CVE scan | Every push |
| Ruff security rules (S rules) | SAST | Every push |
| OWASP ZAP baseline scan | DAST | Weekly against staging |

### Manual

- Full manual penetration test before initial public launch
- Annual repeat, or after any major architectural change
- Scope: API endpoints, authentication flows, payment flow, file upload, admin panel
- Findings tracked in GitHub Issues with severity labels; CRITICAL fixed before next release

### Bug Bounty

Consider a private bug bounty programme via HackerOne or Bugcrowd once the platform is public and stable.

---

## 5. Security Headers

Applied via Django middleware and Nginx:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self' js.stripe.com; frame-src js.stripe.com; img-src 'self' data: *.cloudflare.com; connect-src 'self' api.stripe.com
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

CSP allows Stripe's JavaScript and iframe (required for Stripe Elements) while blocking everything else.

---

## 6. Incident Response Runbook

1. **Detect:** Sentry alert, log anomaly, or external report
2. **Triage:** Assess severity (P1 = data breach or payment fraud; P2 = service degraded; P3 = non-critical issue)
3. **Contain:** Revoke affected tokens, disable affected accounts, take affected service offline if necessary
4. **Investigate:** Review logs, audit trail, Git history
5. **Remediate:** Deploy patch; verify fix in staging before production
6. **Notify:** ICO within 72 hours if personal data breached (UK GDPR); affected users directly if high risk
7. **Post-mortem:** Written within 5 business days; root cause, timeline, actions taken, preventive measures

---

## 7. WCAG 2.1 AA (Accessibility)

The frontend must meet WCAG 2.1 Level AA. Key requirements:

- All images have meaningful `alt` text
- Colour contrast ratio minimum 4.5:1 for normal text
- All interactive elements reachable and operable by keyboard
- Form inputs have associated labels
- Error messages identify the field and describe the issue
- Focus indicators visible on all interactive elements
- Dynamic content changes announced to screen readers via ARIA live regions

Automated checks via `axe-core` run in Playwright end-to-end tests. Manual audit with screen reader (VoiceOver on macOS) before each major release.
