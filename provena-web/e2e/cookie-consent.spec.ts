/**
 * Cookie consent banner: first-time visitor path and hydration safety.
 *
 * Deliberately does NOT pre-seed the cookie_consent cookie. Every other spec
 * seeds it so the fixed banner stays out of the way, which meant the banner's
 * own render path was never exercised. That is exactly the path that produced a
 * React hydration mismatch (server rendered nothing, the client rendered the
 * banner). This spec loads as a fresh visitor and fails on any hydration error.
 */
import { test, expect } from '@playwright/test'

test.describe('Cookie consent', () => {
  test('shows for a first-time visitor without a hydration error', async ({ page }) => {
    const hydrationErrors: string[] = []

    // A hydration mismatch surfaces as an uncaught error and/or a console error
    // mentioning hydration. Capture both so the test fails if either fires.
    page.on('pageerror', (err) => hydrationErrors.push(err.message))
    page.on('console', (msg) => {
      if (msg.type() === 'error' && /hydrat/i.test(msg.text())) {
        hydrationErrors.push(msg.text())
      }
    })

    await page.goto('/')

    // The banner (previously-untested path) must actually render for a visitor
    // with no consent cookie.
    await expect(page.getByRole('dialog', { name: /cookie consent/i })).toBeVisible()

    expect(hydrationErrors, hydrationErrors.join('\n')).toEqual([])
  })

  test('accepting hides the banner and persists across reloads', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /accept all/i }).click()

    const banner = page.getByRole('dialog', { name: /cookie consent/i })
    await expect(banner).toBeHidden()

    await page.reload()
    await expect(banner).toBeHidden()
  })
})
