/**
 * Legal pages and footer links resolve (previously the cookie banner linked
 * /privacy which 404'd).
 */
import { test, expect } from '@playwright/test'

test.describe('Legal pages', () => {
  test('privacy page renders with a cookies section', async ({ page }) => {
    await page.goto('/privacy')
    await expect(page.getByRole('heading', { name: /privacy policy/i, level: 1 })).toBeVisible()
    await expect(page.getByRole('heading', { name: /^cookies$/i })).toBeVisible()
  })

  test('terms page renders', async ({ page }) => {
    await page.goto('/terms')
    await expect(page.getByRole('heading', { name: /terms of service/i, level: 1 })).toBeVisible()
  })

  test('footer legal links resolve from the catalogue', async ({ page }) => {
    await page.goto('/catalogue')
    const footer = page.getByRole('contentinfo')
    await footer.getByRole('link', { name: /privacy policy/i }).click()
    await expect(page).toHaveURL(/\/privacy/)
    await expect(page.getByRole('heading', { name: /privacy policy/i, level: 1 })).toBeVisible()
  })
})
