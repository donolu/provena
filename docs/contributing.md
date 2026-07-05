# Contributing

This guide covers the development workflow for Provena: branching, commit conventions, code standards, testing expectations, and step-by-step patterns for common tasks.

---

## Issue Tracking

All work starts from a GitHub Issue. Before writing code:

1. Check [existing issues](https://github.com/donolu/provena/issues) to avoid duplication
2. If none exists, open one using the appropriate template (Bug report, Feature request, or Chore)
3. Note the issue number — it becomes part of the branch name

Linking a PR to an issue: include `Closes #<number>` in the PR body. GitHub will auto-close the issue when the PR merges.

---

## Branching Strategy

All development happens off `main`. There is no separate `develop` branch.

| Branch prefix | Purpose | Example |
|---|---|---|
| `feature/` | New functionality | `feature/42-add-search` |
| `fix/` | Bug fixes | `fix/17-cart-reservation-race` |
| `chore/` | Tooling, dependencies, config | `chore/88-bump-ruff` |
| `docs/` | Documentation only | `docs/5-deployment-guide` |

**Branch name format:** `<type>/<issue-number>-<short-description>`

The issue number is required. The short description uses lowercase kebab-case. This is enforced in two places:
- The `branch-name` pre-push hook (blocks the push locally before it reaches GitHub)
- The `Branch name check` CI job on every pull request

**Rules:**
- Open a GitHub Issue first; use its number in the branch name
- Branch from `main`; merge back to `main` via pull request
- Delete the branch after merging
- Never commit directly to `main`

---

## Commit Messages

Use the imperative mood and describe the *why*, not just the *what*. One sentence is usually enough.

```
Add TOTP enforcement to supplier middleware

Fix cart reservation not released when order is cancelled

Bump ruff to v0.15 for improved B-series rules
```

**Avoid:**
- `Fix bug` (which bug?)
- `Update code` (what changed?)
- `WIP` commits in pull requests (squash before opening a PR)

---

## Branch Protection

`main` has branch protection rules configured that require:
- A pull request (no direct pushes)
- All four CI checks to pass: `Lint`, `Tests` (API), `Lint and type-check`, `Unit tests` (Web)
- The branch to be up to date with `main` before merging
- No force pushes or branch deletion

> **Note:** Branch protection requires GitHub Pro for private repositories. If the protection is not active yet, the rules above still apply by convention — the pre-push hook and CI workflow enforce the same constraints locally and on the PR.

---

## Pull Request Checklist

Before opening a PR:

- [ ] All CI checks pass (`api.yml`, `web.yml`)
- [ ] Pre-commit hooks pass locally (`pre-commit run --all-files`)
- [ ] New functionality has tests; existing tests still pass
- [ ] Backend test coverage is still above 80% (`pytest --cov`)
- [ ] No new `type: ignore` comments without a comment explaining why
- [ ] API changes that affect the frontend are reflected in `src/lib/api/`
- [ ] Migrations are included if models changed
- [ ] Environment variable additions are reflected in `.env.example`

---

## Code Standards

### Python (provena-api)

**Style:** enforced by `ruff` (linting) and `ruff-format` (formatting). No manual style decisions needed.

**Type hints:** required on all public functions and methods. `mypy` is run on every push. Type stubs for Django and DRF are included (`django-stubs`, `djangorestframework-stubs`).

**Security:** `bandit` runs on every push. `# noqa: SXXX  # nosec BXXX` suppression comments require an inline explanation.

**Key patterns:**

```python
# services.py: functions, not classes; return typed values
def confirm_order(order_id: uuid.UUID, user: User) -> Order:
    order = Order.objects.select_related("supplier").get(id=order_id, buyer=user)
    ...
    return order

# views.py: thin; delegate to services
class ConfirmOrderView(APIView):
    permission_classes = [IsAuthenticated, IsBuyer]

    def post(self, request, pk):
        order = confirm_order(pk, request.user)
        return Response(OrderSerializer(order).data)

# tasks.py: always retry; always capture exceptions
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_confirmation_email(self, order_id: str) -> None:
    try:
        ...
    except Exception as exc:
        logger.exception("Failed to send confirmation email for order %s", order_id)
        raise self.retry(exc=exc) from exc
```

**Tests:** use `pytest` fixtures and `factory-boy` factories. Avoid mocking the database; use `pytest-django`'s `@pytest.mark.django_db`. Aim for one test file per source file.

### TypeScript (provena-web)

**Style:** ESLint with `eslint-config-next`. Zero warnings (`--max-warnings 0`). TypeScript strict mode.

**Key patterns:**

```typescript
// lib/api/: typed functions; never call axios directly in components
export async function getOrders(): Promise<Order[]> {
  const { data } = await api.get<Order[]>('/orders/')
  return data
}

// Components: server components by default; 'use client' only when needed
// Avoid useState/useEffect for data that can be fetched server-side

// Forms: react-hook-form + zod
const schema = z.object({ email: z.string().email() })
type FormData = z.infer<typeof schema>
const { register, handleSubmit } = useForm<FormData>({ resolver: zodResolver(schema) })
```

**Avoid:**
- `any` type (TypeScript strict mode blocks most uses)
- Direct `localStorage` or `document.cookie` access outside `src/lib/`
- `console.log` (ESLint warns; use `console.warn` or `console.error`)
- `<img>` elements with user-supplied `src` where the domain is unknown (ESLint rule `@next/next/no-img-element`; suppress with a comment only when `next/image` cannot be used)

---

## Testing Requirements

### Backend

- **Coverage floor:** 80% (`--cov-fail-under=80` in `pyproject.toml`). PRs that drop coverage below this threshold will not pass CI.
- **What to test:** happy path, permission boundary (unauthenticated, wrong role), validation error, service layer edge cases
- **What not to test:** Django internals, third-party library behaviour, the ORM itself

```bash
# Run with coverage
pytest --cov=apps --cov-report=term-missing

# Run a specific test
pytest apps/orders/tests/test_services.py::TestDeliverSubOrder::test_payout_triggered
```

### Frontend

- **Unit tests:** cover components that have conditional rendering or business logic. Pure presentational components do not need unit tests.
- **E2E tests:** Playwright suites in `provena-web/e2e/`. These require a running backend. Credential-dependent tests skip when env vars are not set.

---

## How to Add a New API Endpoint

**Example: add `GET /api/v1/orders/<id>/timeline/`**

1. **Service layer** — add `get_order_timeline(order_id, user)` to `apps/orders/services.py`

2. **Serializer** — add `OrderTimelineSerializer` to `apps/orders/serializers.py`

3. **View** — add `OrderTimelineView(RetrieveAPIView)` to `apps/orders/views.py`

4. **URL** — register in `apps/orders/urls.py`:
   ```python
   path('<uuid:pk>/timeline/', OrderTimelineView.as_view()),
   ```

5. **Test** — add to `apps/orders/tests/test_views.py`:
   ```python
   def test_timeline_requires_auth(self):
       ...
   def test_timeline_returns_events(self):
       ...
   def test_timeline_forbidden_for_other_user(self):
       ...
   ```

6. **Frontend API function** — add `getOrderTimeline(id: string)` to `provena-web/src/lib/api/orders.ts`

7. **Regenerate TypeScript types** — the generated type file must be updated whenever the API schema changes. Run these two commands from the repo root and commit the result:

   ```bash
   cd provena-api
   python manage.py spectacular --file ../provena-web/schema.yaml

   cd ../provena-web
   npm run generate:types
   ```

   This regenerates `provena-web/src/lib/api/generated/schema.d.ts`. Commit it alongside your API changes. The `Generate OpenAPI client` CI job will fail on your PR if you forget — it exports the schema from your branch and checks whether the committed `schema.d.ts` matches.

The OpenAPI schema (`/api/schema/`) is auto-generated from the views by `drf-spectacular`. Add `@extend_schema` decorators to views for richer schema output.

---

## How to Add a New Django App

Only add a new app if the domain is genuinely new. Extending an existing app is almost always the right choice.

```bash
cd provena-api
python manage.py startapp <name>
```

Then:
1. Add `apps.<name>` to `INSTALLED_APPS` in `config/settings/base.py`
2. Create `apps/<name>/urls.py` and include it in `config/urls.py`
3. Add `apps/<name>/services.py` (even if empty initially)
4. Add `apps/<name>/permissions.py` for any domain-specific permission classes
5. Follow the existing app structure exactly

---

## How to Add a New Frontend Page

1. Create the file at `src/app/<route>/page.tsx`
2. Use a server component if the page is data-heavy and does not need browser APIs:
   ```typescript
   import { getMyData } from '@/lib/api/domain'

   export default async function MyPage() {
     const data = await getMyData()
     return <MyComponent data={data} />
   }
   ```
3. Use `'use client'` only when the page needs `useState`, `useEffect`, browser APIs, or event handlers
4. Add the route to the middleware if it needs authentication:
   - Admin routes are already guarded by the `ADMIN` role check in `src/middleware.ts`
   - Supplier routes are guarded by the `SUPPLIER` role check
   - Buyer routes require `has_session` cookie

---

## How to Add a Celery Task

1. Add to `apps/<domain>/tasks.py`:
   ```python
   @shared_task(bind=True, max_retries=3, default_retry_delay=60)
   def my_task(self, param: str) -> None:
       try:
           do_work(param)
       except Exception as exc:
           logger.exception("my_task failed for %s", param)
           raise self.retry(exc=exc) from exc
   ```

2. For scheduled tasks, add to `CELERY_BEAT_SCHEDULE` in `config/settings/base.py`:
   ```python
   'my-scheduled-task': {
       'task': 'apps.domain.tasks.my_task',
       'schedule': crontab(hour=6, minute=0),
   },
   ```

3. Write a test using `@pytest.mark.django_db` and `unittest.mock.patch` to mock external calls.

---

## API Versioning

The API is versioned via URL prefix: `/api/v1/`. When a breaking change is required:
- Add a new view at `v2/` in the relevant `urls.py`
- Keep `v1/` running until all frontend clients have migrated
- Document the migration in the PR description

Non-breaking additions (new optional fields, new endpoints) do not require a version bump.

---

## Database Migrations

```bash
# After changing a model
python manage.py makemigrations <app_name> --name <descriptive_name>

# Review the generated migration before committing
python manage.py sqlmigrate <app_name> <migration_number>

# Never edit a migration that has already been applied to any shared environment
# (local, staging, or production). Create a new migration instead.
```

If a migration may lock a large table (e.g. adding a non-nullable column), discuss it in the PR and plan a maintenance window.

---

## Adding Environment Variables

1. Add the variable to `provena-api/.env.example` (or `provena-web/.env.example`) with a description and example value
2. Read it in `config/settings/base.py` (or `production.py`) using `env()`:
   ```python
   MY_NEW_SETTING = env('MY_NEW_SETTING', default='fallback')
   ```
3. Document it in [docs/deployment.md](deployment.md) under the Environment Variables Reference section
4. Add it to the Render/Vercel environment variable configuration for staging and production
