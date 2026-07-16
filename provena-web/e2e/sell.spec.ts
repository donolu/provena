/**
 * "Sell on Provena" onboarding at /sell.
 *
 * Covers the public pitch (logged-out) and the full buyer -> supplier
 * application. Requires a running backend; each run registers a unique buyer so
 * it is safe to repeat against the same database.
 */
import { test, expect } from '@playwright/test'

test.describe('Sell on Provena', () => {
  test.beforeEach(async ({ context }) => {
    await context.addCookies([
      { name: 'cookie_consent', value: 'accepted', domain: 'localhost', path: '/' },
    ])
  })

  test('a first-time visitor sees the pitch and a prompt to log in', async ({ page }) => {
    await page.goto('/sell')

    await expect(page.getByRole('heading', { name: /sell on provena/i })).toBeVisible()
    await expect(page.getByText(/how it works/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /log in to apply/i })).toHaveAttribute(
      'href',
      '/login?next=/sell',
    )
  })

  test('a buyer can apply to become a supplier', async ({ page }) => {
    // Register a fresh buyer (this signs them in and lands on the catalogue).
    const email = `e2e-sell-${Date.now()}@example.test`
    await page.goto('/register')
    await page.fill('input[autocomplete="given-name"]', 'Sell')
    await page.fill('input[autocomplete="family-name"]', 'Applicant')
    await page.fill('input[type="email"]', email)
    const passwords = page.locator('input[type="password"]')
    await passwords.nth(0).fill('SuperSecret123!')
    await passwords.nth(1).fill('SuperSecret123!')
    await page.click('button[type="submit"]')
    await page.waitForURL((url) => url.pathname.startsWith('/catalogue'), { timeout: 20_000 })

    // Apply as a supplier.
    await page.goto('/sell')
    await expect(page.getByRole('heading', { name: /tell us about your business/i })).toBeVisible()
    await page.fill('#business_name', `E2E Test Wares ${Date.now()}`)
    await page.fill('#description', 'Handmade goods for testing.')
    await page.getByRole('button', { name: /submit application/i }).click()

    // Pending confirmation with a route through to the supplier dashboard.
    await expect(page.getByText(/application received/i)).toBeVisible({ timeout: 20_000 })
    await expect(page.getByRole('link', { name: /go to your dashboard/i })).toBeVisible()
  })
})
