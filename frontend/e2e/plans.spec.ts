import { expect, test } from '@playwright/test'
import { loginViaUi, mockApi } from './helpers'

test.describe('plans', () => {
  test('guest can browse pricing tiers without signing in', async ({ page }) => {
    await mockApi(page)
    await page.goto('/plans')

    await expect(page.getByTestId('plans-view')).toBeVisible()
    await expect(page.getByTestId('plans-guest-notice')).toBeVisible()
    await expect(page.getByTestId('plan-card-free')).toBeVisible()
    await expect(page.getByTestId('plan-card-pro')).toBeVisible()
    await expect(page.getByTestId('plan-card-business')).toBeVisible()
    await expect(page.getByTestId('plan-popular-badge')).toBeVisible()
    await expect(page.getByTestId('plans-billing-toggle')).toBeVisible()
    await expect(page.getByTestId('plans-current')).toHaveCount(0)
    await expect(page.getByTestId('plan-cta-register').first()).toBeVisible()
    await expect(page.getByTestId('nav-plans')).toBeVisible()
  })

  test('signed-in free user sees current plan and highlighted Pro', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)

    await page.getByTestId('nav-plans').click()
    await expect(page.getByTestId('plans-view')).toBeVisible()
    await expect(page.getByTestId('plans-current')).toContainText(/Free/i)
    await expect(page.getByTestId('plan-cta-current')).toBeDisabled()
    await expect(page.getByTestId('plan-popular-badge')).toBeVisible()
    await expect(page.getByTestId('plans-compare-toggle')).toBeVisible()
    await page.getByTestId('plans-compare-toggle').click()
    await expect(page.getByTestId('plans-compare')).toContainText(/Credits|créditos|Créditos/i)
  })
})
