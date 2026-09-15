import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLibraryStore } from '@/stores/library.store'
import * as userService from '@/services/user.service'

vi.mock('@/services/user.service', () => ({
  listFolders: vi.fn(),
  createFolder: vi.fn(),
  renameFolder: vi.fn(),
  deleteFolder: vi.fn(),
}))

describe('library store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(userService.listFolders).mockReset()
    vi.mocked(userService.createFolder).mockReset()
    vi.mocked(userService.renameFolder).mockReset()
    vi.mocked(userService.deleteFolder).mockReset()
  })

  it('loads folders and updates after create/rename/delete', async () => {
    vi.mocked(userService.listFolders).mockResolvedValueOnce({
      folders: [{ id: 'f1', name: 'Backend', entry_count: 1 }],
      unfiled_count: 2,
    })
    const store = useLibraryStore()
    await store.load()
    expect(store.folders).toHaveLength(1)
    expect(store.unfiledCount).toBe(2)
    expect(store.folderName('f1')).toBe('Backend')

    vi.mocked(userService.createFolder).mockResolvedValueOnce({
      id: 'f2',
      name: 'Personal',
      entry_count: 0,
    })
    await store.create('Personal')
    expect(store.folders.map((item) => item.name)).toContain('Personal')

    vi.mocked(userService.renameFolder).mockResolvedValueOnce({
      id: 'f1',
      name: 'Universidad',
      entry_count: 1,
    })
    await store.rename('f1', 'Universidad')
    expect(store.folderName('f1')).toBe('Universidad')

    vi.mocked(userService.deleteFolder).mockResolvedValueOnce()
    await store.remove('f1')
    expect(store.folderName('f1')).toBeNull()
    expect(store.unfiledCount).toBe(3)
  })
})
