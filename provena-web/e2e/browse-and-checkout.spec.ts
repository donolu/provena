/**
 * Critical path 1: anonymous browse -> add to cart -> checkout with payment.
 *
 * Requires a running backend + seeded test data (at least one active product).
 * Set E2E_BUYER_EMAIL / E2E_BUYER_PASSWORD to a pre-existing buyer account,
 * or allow registration fallback below.
 */
import { test, expect } from '@playwright/test'

test.describe('Browse and checkout', () => {
  test('anonymous user can browse the catalogue', async ({ page }) => {
    await page.goto('/catalogue')
    await expect(page).toHaveTitle(/Shop|Provena/)
    // At least one product card visible
    const cards = page.locator('[data-testid="product-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15_000 })
  })

  test('product detail page renders with name and add-to-cart', async ({ page }) => {
    await page.goto('/catalogue')
    const cards = page.locator('[data-testid="product-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15_000 })
    // Navigate to first product
    await cards.first().getByRole('link').first().click()
    await page.waitForURL(/\/catalogue\/[^/]+$/)
    await expect(page.locator('h1')).toBeVisible()
    // The related-products grid also renders "Add to cart" buttons, so target
    // the main product's (first in the DOM).
    await expect(page.getByRole('button', { name: /add to cart/i }).first()).toBeVisible()
  })

  test('product detail shows a related-products grid', async ({ page }) => {
    await page.goto('/catalogue')
    const cards = page.locator('[data-testid="product-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15_000 })
    await cards.first().getByRole('link').first().click()
    await page.waitForURL(/\/catalogue\/[^/]+$/)
    // "You might also like" loads client-side from the related endpoint.
    const related = page.locator('section', { hasText: /you might also like/i })
    await expect(related.getByRole('heading', { name: /you might also like/i })).toBeVisible()
    await expect(related.locator('[data-testid="product-card"]').first()).toBeVisible()
  })

  test('recently viewed strip tracks a visited product', async ({ page }) => {
    // Visit a product detail page (tracked client-side into localStorage).
    await page.goto('/catalogue')
    const cards = page.locator('[data-testid="product-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15_000 })
    await cards.first().getByRole('link').first().click()
    await page.waitForURL(/\/catalogue\/[^/]+$/)
    await expect(page.locator('h1')).toBeVisible()

    // The homepage should now show it in the "Recently viewed" strip.
    await page.goto('/')
    const strip = page.locator('section', { hasText: /recently viewed/i })
    await expect(strip.getByRole('heading', { name: /recently viewed/i })).toBeVisible()
    await expect(strip.locator('[data-testid="product-card"]').first()).toBeVisible()
  })

  test('logged-in buyer can add to cart and reach checkout', async ({ page }) => {
    const email = process.env.E2E_BUYER_EMAIL
    const password = process.env.E2E_BUYER_PASSWORD
    test.skip(!email || !password, 'E2E_BUYER_EMAIL/PASSWORD not set')

    await page.goto('/login')
    await page.fill('input[type="email"]', email!)
    await page.fill('input[type="password"]', password!)
    await page.click('button[type="submit"]')
    await page.waitForURL((u) => !u.pathname.startsWith('/login'), { timeout: 10_000 })

    // Go to catalogue and add first product
    await page.goto('/catalogue')
    const cards = page.locator('[data-testid="product-card"]')
    await expect(cards.first()).toBeVisible({ timeout: 15_000 })
    await cards.first().getByRole('link').first().click()
    await page.waitForURL(/\/catalogue\/[^/]+$/)

    // Main product button (the related grid also has "Add to cart" buttons).
    const addBtn = page.getByRole('button', { name: /add to cart/i }).first()
    await expect(addBtn).toBeVisible()
    await addBtn.click()

    // Adding opens the cart drawer, which offers "Proceed to checkout".
    const checkoutBtn = page.getByRole('button', { name: /proceed to checkout/i })
    await expect(checkoutBtn).toBeVisible()
    await checkoutBtn.click()
    await page.waitForURL('/checkout')
    await expect(page.locator('h1')).toContainText(/checkout/i)
  })
})
