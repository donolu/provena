/**
 * Critical path 3: admin logs in, reviews a pending supplier, approves/rejects.
 *
 * Set E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD to a staff account.
 */
import { test, expect } from '@playwright/test'
import { loginAs } from './helpers/auth'

test.describe('Admin supplier approval', () => {
  test.beforeEach(async ({ page }) => {
    const email = process.env.E2E_ADMIN_EMAIL
    const password = process.env.E2E_ADMIN_PASSWORD
    test.skip(!email || !password, 'E2E_ADMIN_EMAIL/PASSWORD not set')
    await loginAs(page, email!, password!, process.env.E2E_ADMIN_TOTP_SECRET)
  })

  test('admin dashboard loads', async ({ page }) => {
    await page.goto('/admin/dashboard')
    await expect(page.locator('h1, h2').first()).toBeVisible({ timeout: 10_000 })
  })

  test('admin suppliers list loads', async ({ page }) => {
    await page.goto('/admin/suppliers')
    await expect(page.locator('h1, h2')).toContainText(/supplier/i)
    // Table or empty state
    const table = page.locator('table')
    const empty = page.locator('text=/no suppliers/i')
    const found = (await table.count()) > 0 || (await empty.count()) > 0
    expect(found).toBe(true)
  })

  test('admin can open a pending supplier and see approve/reject buttons', async ({ page }) => {
    await page.goto('/admin/suppliers')

    // Filter to PENDING if filter control exists
    const statusFilter = page.locator('select, [data-testid="status-filter"]').first()
    if (await statusFilter.count() > 0) {
      await statusFilter.selectOption({ label: 'PENDING' })
      await page.waitForTimeout(500)
    }

    const rows = page.locator('table tbody tr')
    const count = await rows.count()
    test.skip(count === 0, 'No pending suppliers to test with')

    // Click first pending supplier row or its view button
    const viewBtn = rows.first().getByRole('button', { name: /view|details|manage/i })
    if (await viewBtn.count() > 0) {
      await viewBtn.click()
    } else {
      await rows.first().click()
    }

    // Approve or reject button should be visible
    const approveBtn = page.getByRole('button', { name: /approve/i })
    const rejectBtn = page.getByRole('button', { name: /reject/i })
    const hasActions = (await approveBtn.count()) > 0 || (await rejectBtn.count()) > 0
    expect(hasActions).toBe(true)
  })

  test('admin audit log page loads', async ({ page }) => {
    await page.goto('/admin/audit-log')
    await expect(page.locator('h1')).toContainText(/audit/i)
    // Either a table or empty state
    const table = page.locator('table')
    const empty = page.locator('text=/no audit entries/i')
    const found = (await table.count()) > 0 || (await empty.count()) > 0
    expect(found).toBe(true)
  })
})
