import type { Page } from '@playwright/test'

export async function loginAs(page: Page, email: string, password: string) {
  await page.goto('/login')
  await page.fill('input[type="email"]', email)
  await page.fill('input[type="password"]', password)
  await page.click('button[type="submit"]')
  // Wait for redirect away from login
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 10_000 })
}
