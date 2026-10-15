import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as credentialsService from '@/services/credentials.service'
import { http } from '@/services/http'
import { i18n } from '@/i18n'

vi.mock('@/services/http', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('credentials.service', () => {
  beforeEach(() => {
    vi.mocked(http.get).mockReset()
    vi.mocked(http.post).mockReset()
    vi.mocked(http.patch).mockReset()
    vi.mocked(http.delete).mockReset()
  })

  it('normalizes _id into id and trims name', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: [
        {
          _id: 'cred-1',
          provider: 'openai',
          user_id: 'u1',
          name: '  Work  ',
          is_default: false,
          status: 'active',
        },
      ],
    })
    const credentials = await credentialsService.listCredentials('openai')
    expect(credentials[0].id).toBe('cred-1')
    expect(credentials[0].name).toBe('Work')
  })

  it('sets default credential', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { id: 'cred-2', provider: 'google', name: 'Backup', is_default: true, status: 'active' },
    })
    const updated = await credentialsService.setDefaultCredential('cred-2')
    expect(http.post).toHaveBeenCalledWith('/user-credentials/cred-2/default')
    expect(updated.is_default).toBe(true)
  })

  it('renames credential', async () => {
    vi.mocked(http.patch).mockResolvedValueOnce({
      data: { id: 'cred-2', provider: 'google', name: 'Personal', is_default: false, status: 'active' },
    })
    const updated = await credentialsService.renameCredential('cred-2', { name: 'Personal' })
    expect(http.patch).toHaveBeenCalledWith('/user-credentials/cred-2', { name: 'Personal' })
    expect(updated.name).toBe('Personal')
  })

  it('deletes by encoded uuid', async () => {
    vi.mocked(http.delete).mockResolvedValueOnce({ status: 204 })
    await credentialsService.deleteCredential('8f14e45f-ea8d-4e6f-9c3b-1a2b3c4d5e6f')
    expect(http.delete).toHaveBeenCalledWith(
      '/user-credentials/8f14e45f-ea8d-4e6f-9c3b-1a2b3c4d5e6f',
    )
  })

  it('rejects delete without id', async () => {
    await expect(credentialsService.deleteCredential('  ')).rejects.toThrow(i18n.global.t('errors.codes.CREDENTIAL_ID_INVALID'))
    expect(http.delete).not.toHaveBeenCalled()
  })

  it('builds display name fallback for unnamed keys', () => {
    expect(
      credentialsService.credentialDisplayName({ name: '', id: 'abcdef12-3456' }, 'Unnamed'),
    ).toBe('Unnamed (abcdef12)')
    expect(credentialsService.credentialDisplayName({ name: 'Work', id: 'x' })).toBe('Work')
  })
})
