import { expect, type Page, type Route } from '@playwright/test'

const API_ORIGIN = process.env.VITE_API_URL || 'http://localhost:8000'

export function appNavLink(page: Page, name: string) {
  return page.getByRole('link', { name, exact: true })
}

export function makeJwt(id = 'user-1', expiresInSeconds = 3600): string {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(
    JSON.stringify({
      id,
      exp: Math.floor(Date.now() / 1000) + expiresInSeconds,
    }),
  ).toString('base64url')
  return `${header}.${payload}.sig`
}

export async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(body),
  })
}

export async function mockApi(
  page: Page,
  options?: { emptyStore?: boolean; failDoc?: boolean; failJob?: boolean },
) {
  let sessionActive = false
  let pollCount = 0
  let queuedSseBody: string | null = null
  let lastSubmittedDocs: string[] = ['doc.pdf']
  const folders = options?.emptyStore
    ? []
    : [
        {
          id: 'lib-1',
          name: 'Backend',
          entry_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]
  let folderSeq = 2
  const storeEntries = options?.emptyStore
    ? []
    : [
        {
          id: 'entry-1',
          user_id: 'user-1',
          name: 'Sample entry',
          original_name: 'doc.pdf',
          library_folder_id: null as string | null,
          created_at: '2026-01-02T10:00:00Z',
          language: 'SPANISH',
          model: 'gpt-4o-mini',
          category: 'education',
          style: 'guide',
          format: 'markdown',
          summary_level: 'moderate',
          source_type: 'documents',
          results: [{ name: 'doc.pdf', status: 'COMPLETED', download_location: 'data/x', index: 0 }],
        },
      ]

  function folderCounts() {
    const counts: Record<string, number> = {}
    let unfiled = 0
    for (const entry of storeEntries) {
      if (!entry.library_folder_id) unfiled += 1
      else counts[entry.library_folder_id] = (counts[entry.library_folder_id] || 0) + 1
    }
    return { counts, unfiled }
  }

  function sseBody(payload: Record<string, unknown>) {
    return [
      `id: ${String(payload.event_id || '1')}`,
      `event: ${String(payload.type)}`,
      `data: ${JSON.stringify(payload)}`,
      '',
      '',
    ].join('\n')
  }

  function queueSummaryEvent(payload: Record<string, unknown>) {
    queuedSseBody = sseBody(payload)
  }

  await page.route(`${API_ORIGIN}/**`, async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const path = url.pathname
    const method = request.method()

    if (path === '/events/stream') {
      if (queuedSseBody) {
        const body = queuedSseBody
        queuedSseBody = null
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          headers: {
            'Cache-Control': 'no-cache',
            Connection: 'keep-alive',
          },
          body,
        })
        return
      }
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        headers: {
          'Cache-Control': 'no-cache',
          Connection: 'keep-alive',
        },
        body: ': keepalive\n\n',
      })
      return
    }

    if (path === '/auth/register' && method === 'POST') {
      sessionActive = true
      await json(route, 201, {
        status: 'success',
        data: { folder: { id: 'f1' }, authenticated: true },
      })
      return
    }

    if (path === '/auth/login' && method === 'POST') {
      const body = request.postDataJSON() as { identity?: string; password?: string }
      if (body?.password === 'wrong') {
        await json(route, 401, { detail: 'Invalid credentials' })
        return
      }
      sessionActive = true
      await json(route, 200, {
        status: 'success',
        data: { authenticated: true },
      })
      return
    }

    if (path === '/auth/refresh' && method === 'POST') {
      if (!sessionActive) {
        await json(route, 401, { detail: 'Refresh token inválido' })
        return
      }
      await json(route, 200, { status: 'success', data: { authenticated: true } })
      return
    }

    if (path === '/auth/logout' && method === 'POST') {
      sessionActive = false
      await json(route, 200, { status: 'success', data: { authenticated: false } })
      return
    }

    if (path === '/auth/session' && method === 'GET') {
      if (!sessionActive) {
        await json(route, 401, { detail: 'Token no proporcionado o nulo' })
        return
      }
      await json(route, 200, {
        status: 'success',
        data: { authenticated: true, user_id: 'user-1' },
      })
      return
    }

    if (path === '/users/me' && method === 'GET') {
      if (!sessionActive) {
        await json(route, 401, { detail: 'Token no proporcionado o nulo' })
        return
      }
      await json(route, 200, {
        status: 'success',
        data: {
          id: 'user-1',
          username: 'tester1',
          email: 'tester1@example.com',
          user_credit: 42,
          folder_id: 'folder-1',
        },
      })
      return
    }

    if (path === '/brevio/languages') {
      await json(route, 200, { status: 'success', data: { languages: ['ENGLISH', 'SPANISH'] } })
      return
    }
    if (path === '/brevio/models') {
      await json(route, 200, {
        status: 'success',
        data: {
          models: ['qwen3:8b', 'gpt-4o-mini'],
          catalog: [
            {
              id: 'qwen3:8b',
              provider: 'ollama',
              access: 'local',
              requires_api_key: false,
              display_name: 'qwen3:8b',
            },
            {
              id: 'gpt-4o-mini',
              provider: 'openai',
              access: 'pay_per_use',
              requires_api_key: true,
              display_name: 'gpt-4o-mini',
            },
          ],
          providers: [
            { id: 'ollama', access: 'local', requires_api_key: false },
            { id: 'openai', access: 'pay_per_use', requires_api_key: true },
          ],
        },
      })
      return
    }
    if (path === '/brevio/categories-styles') {
      await json(route, 200, {
        status: 'success',
        data: {
          advanced_content_combinations: {
            education: [{ style: 'guide', source_types: ['text'] }],
          },
        },
      })
      return
    }
    if (path === '/brevio/output-formats') {
      await json(route, 200, {
        status: 'success',
        data: { output_format_types: ['markdown', 'html'] },
      })
      return
    }
    if (path === '/brevio/summary-levels') {
      await json(route, 200, {
        status: 'success',
        data: { summary_levels: ['concise', 'detailed'] },
      })
      return
    }

    if (path === '/brevio/transcription-providers') {
      await json(route, 200, {
        status: 'success',
        data: {
          environment: 'development',
          providers: [
            {
              id: 'local_whisper',
              implemented: true,
              user_access: true,
              requires_api_key: false,
              access: 'local',
              display_name: 'local_whisper',
            },
          ],
          models: [
            {
              id: 'local_whisper',
              provider: 'local_whisper',
              status: 'stable',
              recommended: true,
              parameters: ['language'],
              display_name: 'local_whisper',
              requires_api_key: false,
              user_access: true,
            },
          ],
          selectable: ['local_whisper'],
          default: 'local_whisper',
          default_model: 'local_whisper',
        },
      })
      return
    }

    if (path === '/brevio/estimate-documents' && method === 'POST') {
      const postData = request.postDataBuffer()
      const bodyText = postData ? postData.toString('latin1') : ''
      const filenames = Array.from(bodyText.matchAll(/filename="([^"]+)"/gi)).map(
        (match) => match[1],
      )
      const docs = (filenames.length ? filenames : ['doc.pdf']).map((filename) => ({
        filename,
        tokens: 100,
        extraction: {
          status: 'ok',
          pages_total: 2,
          pages_with_text: 2,
          pages_without_text: 0,
        },
      }))
      await json(route, 200, {
        status: 'success',
        data: {
          can_process: !options?.failDoc,
          reason: options?.failDoc ? 'Too large' : null,
          estimation: {
            input_tokens: {
              prompt_template: 10,
              documents_content: 100 * docs.length,
              structural: 5,
              total: 15 + 100 * docs.length,
            },
            output_tokens: { minimum: 20, expected: 50, max_ceiling: 100 },
            total_tokens_worst_case: 215,
          },
          documents: docs,
          tokenization: {
            method: 'approx',
            confidence: 'medium',
            estimated_error_margin: 0.1,
          },
          model: {
            name: 'gpt-4o-mini',
            provider: 'openai',
            access: 'pay_per_use',
            context_limit: 128000,
            max_output_tokens: 4096,
            supports_chunking: true,
          },
          pricing: {
            model: 'gpt-4o-mini',
            provider_cost_currency: 'USD',
            platform_currency: 'USD',
            expected_cost: 0.01,
            max_cost: 0.02,
            pricing_version: '1',
          },
          credits: { expected: 1, maximum: 2 },
          chunking: { required: false, calls: 1 },
          estimation_id: 'est-1',
          estimated_at: '2026-01-01T00:00:00Z',
          warnings: [],
        },
      })
      return
    }

    if (path === '/brevio/summary-documents' && method === 'POST') {
      if (options?.failDoc) {
        await json(route, 422, { detail: 'Invalid document' })
        return
      }
      const postData = request.postDataBuffer()
      const bodyText = postData ? postData.toString('latin1') : ''
      const filenames = Array.from(bodyText.matchAll(/filename="([^"]+)"/gi)).map(
        (match) => match[1],
      )
      lastSubmittedDocs = filenames.length ? filenames : ['doc.pdf']
      await json(route, 202, {
        status: 'success',
        data: { message: 'processing' },
        task_id: 'task-1',
        folder_entry_id: 'entry-1',
      })
      queueSummaryEvent({
        type: options?.failJob ? 'summary.failed' : 'summary.completed',
        event_id: '1',
        job_id: 'entry-1',
        document_id: 'doc-1',
        status: options?.failJob ? 'FAILED' : 'COMPLETED',
        timestamp: '2026-01-01T00:00:00Z',
        document_name: lastSubmittedDocs[0] || 'doc.pdf',
        error: options?.failJob ? { code: 'MODEL', message: 'Model error' } : null,
      })
      return
    }

    if (path.startsWith('/brevio/download/')) {
      await route.fulfill({
        status: 200,
        contentType: 'text/markdown',
        body: [
          '# Sample Summary',
          '',
          'Paragraph with **bold** text.',
          '',
          '## Concepts',
          '',
          '- Item one',
          '- [x] Done task',
          '- [ ] Open task',
          '',
          '> Important quote',
          '',
          '```python',
          'async def example():',
          '    return 42',
          '```',
          '',
          '| Concept | Level |',
          '|---------|-------|',
          '| Async   | High  |',
          '',
          '[Docs](https://example.com)',
          '',
          '### Nested section',
          '',
          'More details for reading progress.',
        ].join('\n'),
        headers: { 'Content-Disposition': 'attachment; filename="summary.md"' },
      })
      return
    }

    if (path === '/users/folders') {
      if (method === 'GET') {
        const { counts, unfiled } = folderCounts()
        await json(route, 200, {
          folders: folders.map((folder) => ({ ...folder, entry_count: counts[folder.id] || 0 })),
          unfiled_count: unfiled,
        })
        return
      }
      if (method === 'POST') {
        const body = request.postDataJSON() as { name?: string }
        const folder = {
          id: `lib-${folderSeq++}`,
          name: body?.name || 'New folder',
          entry_count: 0,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        }
        folders.push(folder)
        await json(route, 201, folder)
        return
      }
    }

    if (path.startsWith('/users/folders/') && method === 'PATCH') {
      const folderId = path.split('/').pop() || ''
      const body = request.postDataJSON() as { name?: string }
      const folder = folders.find((item) => item.id === folderId)
      if (folder && body?.name) folder.name = body.name
      await json(route, 200, folder || { id: folderId, name: body?.name || 'Renamed', entry_count: 0 })
      return
    }

    if (path.startsWith('/users/folders/') && method === 'DELETE') {
      const folderId = path.split('/').pop() || ''
      const index = folders.findIndex((item) => item.id === folderId)
      if (index >= 0) folders.splice(index, 1)
      for (const entry of storeEntries) {
        if (entry.library_folder_id === folderId) entry.library_folder_id = null
      }
      await json(route, 200, { status: 'success', id: folderId })
      return
    }

    if (path === '/users/entries/move' && method === 'POST') {
      const body = request.postDataJSON() as { entry_ids?: string[]; library_folder_id?: string | null }
      const succeeded: string[] = []
      for (const id of body.entry_ids || []) {
        const entry = storeEntries.find((item) => item.id === id)
        if (entry) {
          entry.library_folder_id = body.library_folder_id || null
          succeeded.push(id)
        }
      }
      await json(route, 200, { succeeded, failed: [] })
      return
    }

    if (path === '/users/entries/delete' && method === 'POST') {
      const body = request.postDataJSON() as { entry_ids?: string[] }
      const succeeded: string[] = []
      for (const id of body.entry_ids || []) {
        const index = storeEntries.findIndex((item) => item.id === id)
        if (index >= 0) {
          storeEntries.splice(index, 1)
          succeeded.push(id)
        }
      }
      await json(route, 200, { succeeded, failed: [] })
      return
    }

    if (path.startsWith('/users/entries/') && method === 'PATCH') {
      const entryId = path.split('/').pop() || ''
      const body = request.postDataJSON() as { name?: string; library_folder_id?: string | null }
      const entry = storeEntries.find((item) => item.id === entryId)
      if (entry) {
        if (body.name !== undefined) entry.name = body.name
        if (body.library_folder_id !== undefined) entry.library_folder_id = body.library_folder_id
        await json(route, 200, entry)
        return
      }
      await json(route, 404, { code: 'ENTRY_NOT_FOUND', message: 'ENTRY_NOT_FOUND' })
      return
    }

    if (path === '/users/entries') {
      if (method === 'GET') {
        await json(route, 200, { entries: storeEntries })
        return
      }

      if (method === 'POST') {
        pollCount += 1
        if (options?.failJob) {
          await json(route, 200, {
            entries: [
              {
                id: 'entry-1',
                user_id: 'user-1',
                name: 'Job entry',
                results: [
                  {
                    name: 'doc.pdf',
                    status: 'FAILED',
                    phase: 'FAILED',
                    error_message: 'Model error',
                    download_location: null,
                  },
                ],
              },
            ],
          })
          return
        }
        const status = pollCount < 2 ? 'PROCESSING' : 'COMPLETED'
        await json(route, 200, {
          entries: [
            {
              id: 'entry-1',
              user_id: 'user-1',
              name:
                lastSubmittedDocs.length > 1
                  ? 'Summary entry-1'
                  : 'Job entry',
              original_name: lastSubmittedDocs.join('; '),
              results: lastSubmittedDocs.map((name, index) => ({
                name,
                index,
                status,
                phase: status === 'PROCESSING' ? 'MAP' : 'COMPLETED',
                download_location: status === 'COMPLETED' ? `data/x/${index}` : null,
              })),
            },
          ],
        })
        return
      }
    }

    if (path.startsWith('/users/entries/') && method === 'DELETE') {
      const entryId = path.split('/').pop() || ''
      const index = storeEntries.findIndex((item) => item.id === entryId)
      if (index >= 0) storeEntries.splice(index, 1)
      await json(route, 200, { status: 'success', message: 'Entry deleted', id: entryId })
      return
    }

    if (path.startsWith('/user-credentials')) {
      if (method === 'GET') {
        await json(route, 200, [])
        return
      }
      if (method === 'POST') {
        await json(route, 201, {
          _id: 'cred-1',
          id: 'cred-1',
          user_id: 'user-1',
          provider: 'openai',
          is_default: false,
          status: 'active',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        })
        return
      }
      if (method === 'DELETE') {
        await route.fulfill({ status: 204, body: '' })
        return
      }
    }

    await json(route, 404, { detail: `Unhandled mock: ${method} ${path}` })
  })
}

export async function loginViaUi(page: Page) {
  await page.goto('/auth/login')
  await page.evaluate(() => {
    localStorage.clear()
    localStorage.setItem('brevio_locale', 'en')
  })
  await page.reload()
  await expect(page.locator('#login-identity')).toBeVisible({ timeout: 15_000 })
  await page.locator('#login-identity').fill('tester1')
  await page.locator('#login-password').fill('Aa1@aaaa')
  await page.getByTestId('login-submit').click()
  await page.waitForURL('**/summary')
  await expect(page.getByTestId('summary-view')).toBeVisible()
  // Catalog defaults (language/model/…) fill asynchronously after /brevio/* loads.
  await expect(page.getByTestId('summary-params')).toContainText(/English|Spanish/i, {
    timeout: 15_000,
  })
}
