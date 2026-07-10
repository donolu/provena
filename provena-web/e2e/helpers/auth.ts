import type { Page } from '@playwright/test'
import { generateTotp } from './totp'

/**
 * Log in through the UI. When a TOTP secret is supplied (supplier/admin roles,
 * which enforce two-factor auth), the second step is completed automatically.
 */
export async function loginAs(page: Page, email: string, password: string, totpSecret?: string) {
  await page.goto('/login')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')

  if (totpSecret) {
    // Two-step verification screen shown for TOTP-enabled accounts.
    const codeInput = page.locator('input[autocomplete="one-time-code"]')
    await codeInput.waitFor({ state: 'visible', timeout: 10_000 })
    await codeInput.fill(generateTotp(totpSecret))
    await page.getByRole('button', { name: /verify/i }).click()
  }

  // Wait for redirect away from login
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 10_000 })
}
