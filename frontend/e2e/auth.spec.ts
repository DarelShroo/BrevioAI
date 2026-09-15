import { expect, test } from '@playwright/test'
import { appNavLink, loginViaUi, mockApi } from './helpers'

test.describe('auth flows', () => {
  test('register then lands in app', async ({ page }) => {
    await mockApi(page)
    await page.goto('/auth/register')
    await page.getByTestId('register-username').fill('tester1')
    await page.getByTestId('register-email').fill('tester1@example.com')
    await page.locator('#register-password').fill('Aa1@aaaa')
    await page.keyboard.press('Escape')
    await page.getByTestId('register-submit').click({ force: true })
    await page.waitForURL('**/summary')
    await expect(page.getByTestId('summary-view')).toBeVisible()
  })

  test('login then open profile', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await appNavLink(page, 'Settings').click()
    await expect(page.getByTestId('profile-view')).toBeVisible()
    await expect(page.getByText('tester1@example.com')).toBeVisible()
  })

  test('login errors show message', async ({ page }) => {
    await mockApi(page)
    await page.goto('/auth/login')
    await page.getByTestId('login-identity').fill('tester1')
    await page.locator('#login-password').fill('wrong')
    await page.getByTestId('login-submit').click()
    await expect(page.getByText(/Invalid credentials/i)).toBeVisible()
  })

  test('validation blocks empty login', async ({ page }) => {
    await mockApi(page)
    await page.goto('/auth/login')
    await page.getByTestId('login-identity').fill('ab')
    await page.locator('#login-password').fill('x')
    await page.getByTestId('login-submit').click()
    await expect(page.getByText(/valid username or email/i)).toBeVisible()
  })

  test('logout redirects protected routes', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await page.getByRole('button', { name: 'Log out' }).first().click()
    await page.waitForURL('**/auth/login')
    await page.goto('/summary')
    await page.waitForURL('**/auth/login**')
  })
})
