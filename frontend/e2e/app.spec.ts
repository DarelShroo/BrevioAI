import { expect, test } from '@playwright/test'
import { appNavLink, loginViaUi, mockApi, json } from './helpers'

test.describe('summary + store', () => {
  test('create summary processes then completes', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)

    await page.getByTestId('estimate-btn').click()
    await expect(page.getByText(/Choose at least one PDF or DOCX/i)).toBeVisible()

    await page.setInputFiles('input[type="file"]', {
      name: 'doc.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 mock'),
    })

    await page.getByTestId('estimate-btn').click()
    await expect(page.getByTestId('estimate-panel')).toBeVisible()
    await page.getByTestId('submit-docs-btn').click()
    await expect(page.getByTestId('job-status')).toContainText(/PROCESSING|COMPLETED/)
    await expect(page.getByText(/Summary ready/i)).toBeVisible({ timeout: 15_000 })
    await expect(page.getByText(/doc.pdf/i).first()).toBeVisible()
    await expect(page.getByTestId('download-btn')).toBeVisible({ timeout: 15_000 })
  })

  test('rejects invalid file extension', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await page.setInputFiles('input[type="file"]', {
      name: 'notes.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('hello'),
    })
    await expect(page.getByTestId('file-picker-error')).toBeVisible()
    await expect(page.getByTestId('file-picker-error')).toContainText(/PDF and DOCX|MP3/i)
  })

  test('accepts multiple documents in one job', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)

    await page.setInputFiles('input[type="file"]', [
      {
        name: 'alpha.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('%PDF-1.4 a'),
      },
      {
        name: 'beta.pdf',
        mimeType: 'application/pdf',
        buffer: Buffer.from('%PDF-1.4 b'),
      },
    ])

    await expect(page.getByTestId('file-picker-count')).toContainText(/2/)
    await expect(page.getByTestId('file-picker-list')).toContainText('alpha.pdf')
    await expect(page.getByTestId('file-picker-list')).toContainText('beta.pdf')

    await page.getByTestId('estimate-btn').click()
    await expect(page.getByTestId('estimate-panel')).toBeVisible()
    await expect(page.getByTestId('estimate-documents')).toContainText('alpha.pdf')
    await expect(page.getByTestId('estimate-documents')).toContainText('beta.pdf')

    await page.getByTestId('submit-docs-btn').click()
    await expect(page.getByTestId('job-results')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('job-results')).toContainText('alpha.pdf')
    await expect(page.getByTestId('job-results')).toContainText('beta.pdf')
    await expect(page.getByTestId('download-btn')).toHaveCount(2, { timeout: 15_000 })
  })

  test('store shows entry detail and filters', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await expect(page.getByTestId('store-view')).toBeVisible()
    await expect(page.getByTestId('store-grid')).toBeVisible()
    await expect(page.getByText('Sample entry')).toBeVisible()
    await page.getByTestId('store-filter').fill('Sample')
    await expect(page.getByTestId('store-entry-card')).toHaveCount(1)
    await page.getByTestId('store-view-btn').first().click()
    await expect(page.getByTestId('store-detail')).toBeVisible()
    await expect(page.getByTestId('store-detail')).toContainText(/SPANISH|gpt-4o-mini/i)
  })

  test('organizes summaries with folders, selection, move and rename', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await expect(page.getByTestId('store-view')).toBeVisible()
    await expect(page.getByText('Sample entry')).toBeVisible()

    await page.getByTestId('store-create-folder').click()
    await page.getByTestId('store-name-input').fill('Universidad')
    await page.getByTestId('store-dialog-save').click()
    await expect(page.getByTestId('store-name-input')).toHaveCount(0)
    await expect(page.getByText('Universidad')).toBeVisible()

    await page.getByTestId('store-entry-select').first().check()
    await expect(page.getByTestId('store-bulk-bar')).toBeVisible()
    await page.getByTestId('store-move-selected').click()
    await page.getByTestId('store-move-select').click()
    await page.getByRole('option', { name: 'Universidad' }).click()
    await page.getByTestId('store-dialog-save').click()
    await expect(page.getByTestId('store-dialog-save')).toHaveCount(0)

    await page.locator('[data-testid^="store-scope-folder-"]').filter({ hasText: 'Universidad' }).click()
    await expect(page.getByTestId('store-entry-card')).toContainText('Sample entry')

    await page.getByTestId('store-view-btn').first().click()
    await page.getByTestId('store-detail-rename').click()
    await page.getByTestId('store-name-input').fill('Asyncio - Apuntes')
    await page.getByTestId('store-dialog-save').click()
    await expect(page.getByTestId('store-name-input')).toHaveCount(0)
    await expect(page.getByTestId('store-entry-card')).toContainText('Asyncio - Apuntes')
    await page.keyboard.press('Escape')

    await page.getByTestId('store-entry-select').first().check()
    await page.getByTestId('store-move-selected').click()
    await page.getByTestId('store-move-select').click()
    await page.getByRole('option', { name: 'Unfiled' }).click()
    await page.getByTestId('store-dialog-save').click()
    await expect(page.getByTestId('store-dialog-save')).toHaveCount(0)
    await page.getByTestId('store-scope-unfiled').click()
    await expect(page.getByTestId('store-entry-card')).toContainText('Asyncio - Apuntes')

    await page.getByTestId('store-scope-all').click()
    await page.getByTestId('store-create-folder').click()
    await page.getByTestId('store-name-input').fill('Personal')
    await page.getByTestId('store-dialog-save').click()
    await expect(page.getByText('Personal')).toBeVisible()
    await page.getByTestId('store-entry-select').first().check()
    await page.getByTestId('store-move-selected').click()
    await page.getByTestId('store-move-select').click()
    await page.getByRole('option', { name: 'Personal' }).click()
    await page.getByTestId('store-dialog-save').click()
    await page.locator('[data-testid^="store-scope-folder-"]').filter({ hasText: 'Personal' }).click()
    await expect(page.getByTestId('store-entry-card')).toContainText('Asyncio - Apuntes')
    page.once('dialog', (dialog) => dialog.accept())
    await page.getByTestId('store-delete-folder').click()
    await expect(page.locator('[data-testid^="store-scope-folder-"]').filter({ hasText: 'Personal' })).toHaveCount(0)
    await page.getByTestId('store-scope-unfiled').click()
    await expect(page.getByTestId('store-entry-card')).toContainText('Asyncio - Apuntes')

    await page.getByTestId('store-scope-all').click()
    page.once('dialog', (dialog) => dialog.accept())
    await page.getByTestId('store-delete-btn').first().click()
    await expect(page.getByTestId('store-entry-card')).toHaveCount(0)
  })

  test('store can delete an entry', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await expect(page.getByTestId('store-entry-card')).toHaveCount(1)
    page.once('dialog', (dialog) => dialog.accept())
    await page.getByTestId('store-delete-btn').first().click()
    await expect(page.getByTestId('store-entry-card')).toHaveCount(0)
  })

  test('empty folder state has CTA', async ({ page }) => {
    await mockApi(page, { emptyStore: true })
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await expect(page.getByText(/Your (library|store) is empty/i)).toBeVisible()
    await page.getByTestId('store-create-folder').click()
    await page.getByTestId('store-name-input').fill('Universidad')
    await page.getByTestId('store-dialog-save').click()
    await page.locator('[data-testid^="store-scope-folder-"]').filter({ hasText: 'Universidad' }).click()
    await expect(page.getByText(/This folder is empty/i)).toBeVisible()
    await expect(page.getByTestId('store-empty-folder-cta')).toBeVisible()
  })

  test('empty store state has CTA', async ({ page }) => {
    await mockApi(page, { emptyStore: true })
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await expect(page.getByText(/Your (library|store) is empty/i)).toBeVisible()
    await expect(page.getByTestId('store-empty-cta')).toBeVisible()
  })

  test('failed document estimate blocks submit', async ({ page }) => {
    await mockApi(page, { failDoc: true })
    await loginViaUi(page)
    await page.setInputFiles('input[type="file"]', {
      name: 'doc.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 mock'),
    })
    await page.getByTestId('estimate-btn').click()
    await expect(page.getByTestId('estimate-panel')).toContainText(/Too large|Cannot process/i)
    await page.getByTestId('submit-docs-btn').click()
    await expect(
      page.getByTestId('summary-view').locator('.p-message-error, [data-p="error"]').first(),
    ).toBeVisible()
    await expect(page.getByTestId('summary-view')).toContainText(/cannot be processed|Too large/i)
  })

  test('failed job shows FAILED status', async ({ page }) => {
    await mockApi(page, { failJob: true })
    await loginViaUi(page)
    await page.setInputFiles('input[type="file"]', {
      name: 'doc.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 mock'),
    })
    await page.getByTestId('estimate-btn').click()
    await expect(page.getByTestId('estimate-panel')).toBeVisible()
    await page.getByTestId('submit-docs-btn').click()
    await expect(page.getByText(/Error generating the summary|Summary failed/i)).toBeVisible({ timeout: 15_000 })
    await expect(page.getByTestId('job-status')).toContainText(/FAILED/, { timeout: 15_000 })
    await expect(page.getByText(/Model error/i).first()).toBeVisible()
    await expect(page.getByTestId('download-btn')).toHaveCount(0)
  })

  test('backend unavailable on login', async ({ page }) => {
    await page.route('**/users/me', async (route) => {
      if (route.request().resourceType() === 'document') {
        return route.continue()
      }
      await route.abort('failed')
    })
    await page.route('**/auth/login', async (route) => {
      if (route.request().resourceType() === 'document') {
        return route.continue()
      }
      await route.abort('failed')
    })
    await page.goto('/auth/login')
    await page.locator('#login-identity').fill('tester1')
    await page.locator('#login-password').fill('Aa1@aaaa')
    await page.getByTestId('login-submit').click()
    await expect(page.getByText(/Backend unavailable|Network|failed/i)).toBeVisible()
  })

  test('401 on profile clears session', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await page.route('**/users/me', async (route) => {
      await json(route, 401, { detail: 'Token expirado' })
    })
    await appNavLink(page, 'profile').click()
    await page.waitForURL('**/auth/login**', { timeout: 10_000 }).catch(async () => {
      await page.goto('/profile')
      await page.waitForURL('**/auth/login**')
    })
  })

  test('direct protected route redirects when logged out', async ({ page }) => {
    await mockApi(page)
    await page.goto('/store')
    await page.waitForURL('**/auth/login**')
  })

  test('refresh keeps session', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await page.reload()
    await expect(page.getByTestId('summary-view')).toBeVisible()
  })

  test('back/forward navigation works', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await expect(page.getByTestId('store-view')).toBeVisible()
    await page.goBack()
    await expect(page.getByTestId('summary-view')).toBeVisible()
    await page.goForward()
    await expect(page.getByTestId('store-view')).toBeVisible()
  })

  test('responsive drawer and store on mobile', async ({ page }) => {
    await mockApi(page)
    await page.setViewportSize({ width: 390, height: 844 })
    await loginViaUi(page)
    await page.getByLabel('Open navigation').click()
    await expect(appNavLink(page, 'Store')).toBeVisible()
    await appNavLink(page, 'Store').click()
    await expect(page.getByTestId('store-view')).toBeVisible()
    await expect(page.getByTestId('store-grid')).toBeVisible()
  })

  test('tablet layout keeps store usable', async ({ page }) => {
    await mockApi(page)
    await page.setViewportSize({ width: 820, height: 1024 })
    await loginViaUi(page)
    await page.getByLabel('Open navigation').click()
    await appNavLink(page, 'Store').click()
    await expect(page.getByTestId('store-entry-card')).toBeVisible()
  })
})

test.describe('auth edge cases', () => {
  test('missing session is treated as logged out', async ({ page }) => {
    await mockApi(page)
    await page.goto('/summary')
    await page.waitForURL('**/auth/login**')
  })
})
