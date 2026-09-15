import { beforeEach, describe, expect, it, vi } from 'vitest'
import { http } from '@/services/http'
import * as userService from '@/services/user.service'

vi.mock('@/services/http', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('user.service library', () => {
  beforeEach(() => {
    vi.mocked(http.get).mockReset()
    vi.mocked(http.post).mockReset()
    vi.mocked(http.patch).mockReset()
    vi.mocked(http.delete).mockReset()
  })

  it('lists folders and unfiled count', async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: { folders: [{ id: 'f1', name: 'Backend', entry_count: 2 }], unfiled_count: 3 },
    } as any)
    await expect(userService.listFolders()).resolves.toEqual({
      folders: [{ id: 'f1', name: 'Backend', entry_count: 2 }],
      unfiled_count: 3,
    })
  })

  it('creates, renames and deletes folders', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({
      data: { id: 'f1', name: 'Mis apuntes', entry_count: 0 },
    } as any)
    await expect(userService.createFolder('Mis apuntes')).resolves.toMatchObject({
      name: 'Mis apuntes',
    })

    vi.mocked(http.patch).mockResolvedValueOnce({
      data: { id: 'f1', name: 'Apuntes universidad', entry_count: 0 },
    } as any)
    await expect(userService.renameFolder('f1', 'Apuntes universidad')).resolves.toMatchObject({
      name: 'Apuntes universidad',
    })

    vi.mocked(http.delete).mockResolvedValueOnce({} as any)
    await userService.deleteFolder('f1')
    expect(http.delete).toHaveBeenCalledWith('/users/folders/f1')
  })

  it('renames, moves and bulk deletes entries', async () => {
    vi.mocked(http.patch).mockResolvedValueOnce({
      data: { id: 'e1', user_id: 'u1', name: 'Asyncio - Apuntes', results: [] },
    } as any)
    await expect(userService.patchEntry('e1', { name: 'Asyncio - Apuntes' })).resolves.toMatchObject({
      name: 'Asyncio - Apuntes',
    })

    vi.mocked(http.post).mockResolvedValueOnce({
      data: { succeeded: ['e1', 'e2'], failed: [] },
    } as any)
    await expect(userService.moveEntries(['e1', 'e2'], null)).resolves.toEqual({
      succeeded: ['e1', 'e2'],
      failed: [],
    })
    expect(http.post).toHaveBeenCalledWith('/users/entries/move', {
      entry_ids: ['e1', 'e2'],
      library_folder_id: null,
    })

    vi.mocked(http.post).mockResolvedValueOnce({
      data: { succeeded: ['e1'], failed: [{ id: 'missing', code: 'ENTRY_NOT_FOUND' }] },
    } as any)
    await expect(userService.deleteEntries(['e1', 'missing'])).resolves.toMatchObject({
      succeeded: ['e1'],
    })
  })
})
