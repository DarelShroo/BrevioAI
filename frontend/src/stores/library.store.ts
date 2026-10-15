import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as userService from '@/services/user.service'
import type { LibraryFolder } from '@/types/user'
import { parseApiError } from '@/utils/errors'

export const useLibraryStore = defineStore('library', () => {
  const folders = ref<LibraryFolder[]>([])
  const unfiledCount = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const byId = computed(() => {
    const map: Record<string, LibraryFolder> = {}
    for (const folder of folders.value) {
      map[folder.id] = folder
    }
    return map
  })

  async function load() {
    loading.value = true
    error.value = null
    try {
      const payload = await userService.listFolders()
      folders.value = payload.folders
      unfiledCount.value = payload.unfiled_count
    } catch (err) {
      error.value = parseApiError(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function create(name: string) {
    const folder = await userService.createFolder(name)
    folders.value = [...folders.value, folder].sort((a, b) => a.name.localeCompare(b.name))
    return folder
  }

  async function rename(folderId: string, name: string) {
    const folder = await userService.renameFolder(folderId, name)
    folders.value = folders.value.map((item) => (item.id === folderId ? { ...item, ...folder } : item))
    return folder
  }

  async function remove(folderId: string) {
    const folder = folders.value.find((item) => item.id === folderId)
    await userService.deleteFolder(folderId)
    folders.value = folders.value.filter((item) => item.id !== folderId)
    unfiledCount.value += folder?.entry_count || 0
  }

  function folderName(folderId: string | null | undefined) {
    if (!folderId) return null
    return byId.value[folderId]?.name || null
  }

  return {
    folders,
    unfiledCount,
    loading,
    error,
    byId,
    load,
    create,
    rename,
    remove,
    folderName,
  }
})
