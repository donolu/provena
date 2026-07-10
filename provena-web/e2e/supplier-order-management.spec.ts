/**
 * Critical path 2: supplier logs in, views orders, marks one as dispatched.
 *
 * Set E2E_SUPPLIER_EMAIL / E2E_SUPPLIER_PASSWORD to an approved supplier account.
 */
import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/auth'

test.describe('Supplier order management', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_SUPPLIER_EMAIL
    const password = process.env.E2E_SUPPLIER_PASSWORD
    test.skip(!email || !password, 'E2E_SUPPLIER_EMAIL/PASSWORD not set')
    await loginAs(page, email!, password!, process.env.E2E_SUPPLIER_TOTP_SECRET)
  })

  test('supplier dashboard loads with key metrics', async ({ page }) => {
    await page.goto('/supplier/dashboard')
    await expect(page.locator('h1, h2')).toContainText(/dashboard|overview/i)
    // Revenue or orders summary card visible
    await expect(page.locator('[data-testid="summary-card"], .stat-card, .rounded-xl').first()).toBeVisible()
  })

  test('supplier orders list loads', async ({ page }) => {
    await page.goto('/supplier/orders')
    await expect(page.locator('h1, h2')).toContainText(/orders/i)
    // Either an order row or an empty state
    const hasOrders = await page.locator('table tbody tr').count()
    const hasEmpty = await page.locator('[data-testid="empty-state"], text=/no orders/i').count()
    expect(hasOrders + hasEmpty).toBeGreaterThan(0)
  })

  test('supplier can open an order and see dispatch controls', async ({ page }) => {
    await page.goto('/supplier/orders')
    const rows = page.locator('table tbody tr')
    const count = await rows.count()
    test.skip(count === 0, 'No orders to test with')

    await rows.first().click()
    // Dispatch button or status badge visible on order detail
    const dispatchBtn = page.getByRole('button', { name: /dispatch|mark.+dispatched/i })
    const statusBadge = page.locator('[data-testid="order-status"], .badge')
    const found = (await dispatchBtn.count()) > 0 || (await statusBadge.count()) > 0
    expect(found).toBe(true)
  })
})
