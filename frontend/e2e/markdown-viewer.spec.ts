import { expect, test } from '@playwright/test'
import { appNavLink, loginViaUi, mockApi } from './helpers'

test.describe('markdown summary viewer', () => {
  test('renders summary markdown in store detail', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await expect(page.getByTestId('store-view')).toBeVisible()
    await page.getByTestId('store-view-btn').first().click()

    await expect(page.getByTestId('store-detail')).toBeVisible()
    await expect(page.getByTestId('summary-reader')).toBeVisible()
    await expect(page.getByTestId('markdown-viewer')).toBeVisible()
    await expect(page.getByTestId('markdown-body')).toContainText('Sample Summary')
    await expect(page.getByTestId('markdown-body').locator('h1')).toContainText('Sample Summary')
    await expect(page.getByTestId('markdown-body').locator('table')).toBeVisible()
    await expect(page.getByTestId('markdown-body').locator('blockquote')).toContainText('Important quote')
    await expect(page.getByTestId('markdown-body').locator('.md-code')).toBeVisible()
    await expect(page.getByTestId('markdown-toc')).toBeVisible()
    await expect(page.getByTestId('markdown-toc').getByRole('link', { name: 'Concepts' })).toBeVisible()
  })

  test('navigates headings copies code and stays responsive', async ({ page }) => {
    await mockApi(page)
    await loginViaUi(page)
    await appNavLink(page, 'Store').click()
    await page.getByTestId('store-view-btn').first().click()

    const body = page.getByTestId('markdown-body')
    await expect(body).toBeVisible()

    await page.getByTestId('markdown-toc').getByRole('link', { name: 'Concepts' }).click()
    await expect(body.locator('#concepts')).toBeAttached()
    await body.locator('#concepts').scrollIntoViewIfNeeded()
    await expect(body.locator('#concepts')).toBeInViewport()

    await page.evaluate(() => {
      Object.defineProperty(navigator, 'clipboard', {
        configurable: true,
        value: {
          writeText: async () => undefined,
        },
      })
    })

    const copy = body.locator('.md-code__copy').first()
    await body.evaluate((el) => {
      el.querySelector('.md-code')?.scrollIntoView({ block: 'center', inline: 'nearest' })
    })
    await copy.click({ force: true })
    await expect(copy).toContainText(/Copied|Copiado|Copy/i)

    await page.setViewportSize({ width: 390, height: 844 })
    await expect(page.getByTestId('markdown-viewer')).toBeVisible()
    const hasPageOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
    })
    expect(hasPageOverflow).toBe(false)

    await page.evaluate(() => {
      document.documentElement.setAttribute('data-theme', 'dark')
    })
    await expect(page.getByTestId('markdown-viewer')).toBeVisible()
    await expect(body.locator('a[href="https://example.com"]')).toHaveAttribute(
      'rel',
      /noopener/,
    )
    await expect(body.locator('input[type="checkbox"]').first()).toBeDisabled()
  })
})
