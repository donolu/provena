/**
 * Password reset flow via /reset-password.
 *
 * The page branches on the `?token` query param: request mode (enter email) and
 * confirm mode (token from the email link, plus a new password). Requires a
 * running backend for the request/confirm API calls.
 */
import { test, expect } from '@playwright/test'

test.describe('Password reset', () => {
  // Pre-seed cookie consent so the fixed-bottom banner cannot intercept clicks.
  test.beforeEach(async ({ context }) => {
    await context.addCookies([
      { name: 'cookie_consent', value: 'accepted', domain: 'localhost', path: '/' },
    ])
  })

  test('request mode: submitting an email shows the check-your-email confirmation', async ({ page }) => {
    await page.goto('/reset-password')
    await page.fill('input[type="email"]', `e2e-reset-${Date.now()}@example.test`)
    await page.click('button[type="submit"]')
    await expect(page.getByRole('heading', { name: /check your email/i })).toBeVisible()
  })

  test('confirm mode: mismatched passwords are rejected before submitting', async ({ page }) => {
    await page.goto('/reset-password?token=any-token')
    const passwords = page.locator('input[type="password"]')
    await passwords.nth(0).fill('SuperSecret123!')
    await passwords.nth(1).fill('DifferentPass456!')
    await page.click('button[type="submit"]')
    await expect(page.getByText(/passwords do not match/i)).toBeVisible()
  })

  test('confirm mode: an invalid token surfaces an error', async ({ page }) => {
    await page.goto('/reset-password?token=invalid-expired-token')
    const passwords = page.locator('input[type="password"]')
    await passwords.nth(0).fill('SuperSecret123!')
    await passwords.nth(1).fill('SuperSecret123!')
    await page.click('button[type="submit"]')
    await expect(page.getByText(/invalid or has expired|invalid or expired/i)).toBeVisible({ timeout: 15_000 })
  })
})
