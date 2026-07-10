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
    // Wait for the async load to settle into a table or an empty state.
    await expect(
      page.locator('table').or(page.getByText(/no suppliers/i)).first()
    ).toBeVisible()
  })

  test('admin can open a pending supplier and see approve/reject buttons', async ({ page }) => {
    await page.goto('/admin/suppliers')
    // Wait for the table to load (the seed includes a pending supplier).
    await expect(page.locator('table tbody tr').first()).toBeVisible()

    // A PENDING supplier renders inline Approve / Reject actions in its row.
    const approveBtn = page.getByRole('button', { name: /approve/i })
    const rejectBtn = page.getByRole('button', { name: /reject/i })
    const hasActions = (await approveBtn.count()) > 0 || (await rejectBtn.count()) > 0
    expect(hasActions).toBe(true)
  })

  test('admin audit log page loads', async ({ page }) => {
    await page.goto('/admin/audit-log')
    await expect(page.locator('h1')).toContainText(/audit/i)
    // Wait for the async load to settle into a table or an empty state.
    await expect(
      page.locator('table').or(page.getByText(/no audit entries/i)).first()
    ).toBeVisible()
  })
})
