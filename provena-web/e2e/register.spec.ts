/**
 * Buyer self-registration through the /register page.
 *
 * Requires a running backend (registration posts to /auth/register/). Each run
 * uses a unique email so it is safe to repeat against the same database.
 */
import { test, expect } from '@playwright/test'

test.describe('Registration', () => {
  // Pre-seed cookie consent so the fixed-bottom banner never renders. Otherwise
  // it can appear late and intercept the form's submit button (flaky click).
  test.beforeEach(async ({ context }) => {
    await context.addCookies([
      { name: 'cookie_consent', value: 'accepted', domain: 'localhost', path: '/' },
    ])
  })

  test('a new buyer can create an account and lands on the catalogue', async ({ page }) => {
    const email = `e2e-signup-${Date.now()}@example.test`
    await page.goto('/register')

    await page.fill('input[autocomplete="given-name"]', 'New')
    await page.fill('input[autocomplete="family-name"]', 'Buyer')
    await page.fill('input[type="email"]', email)
    const passwords = page.locator('input[type="password"]')
    await passwords.nth(0).fill('SuperSecret123!')
    await passwords.nth(1).fill('SuperSecret123!')
    await page.click('button[type="submit"]')

    // Buyers are signed in and redirected to the catalogue after signup.
    await page.waitForURL((url) => url.pathname.startsWith('/catalogue'), { timeout: 20_000 })
  })

  test('mismatched passwords are rejected before submitting', async ({ page }) => {
    await page.goto('/register')
    await page.fill('input[type="email"]', `e2e-mismatch-${Date.now()}@example.test`)
    const passwords = page.locator('input[type="password"]')
    await passwords.nth(0).fill('SuperSecret123!')
    await passwords.nth(1).fill('DifferentPass456!')
    await page.click('button[type="submit"]')

    await expect(page.getByText(/passwords do not match/i)).toBeVisible()
    await expect(page).toHaveURL(/\/register/)
  })
})
