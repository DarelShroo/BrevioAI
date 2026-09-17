import type { AxiosRequestConfig } from 'axios'
import { http } from '@/services/http'
import type { ApiEnvelope } from '@/types/api'
import type {
  BulkEntriesResponse,
  EntriesPollRequest,
  FolderEntry,
  GetEntriesResponse,
  LibraryFolder,
  ListLibraryFoldersResponse,
  UserProfile,
} from '@/types/user'

export async function getMe(options?: { skipSessionExpired?: boolean }): Promise<UserProfile> {
  const { data } = await http.get<ApiEnvelope<UserProfile>>('/users/me', {
    skipSessionExpired: options?.skipSessionExpired === true,
  } as AxiosRequestConfig)
  return data.data
}

export async function listEntries(folderId?: string | null): Promise<FolderEntry[]> {
  const { data } = await http.get<GetEntriesResponse>('/users/entries', {
    params: folderId ? { folder_id: folderId } : undefined,
  })
  return data.entries || []
}

export async function pollEntries(entriesRefs: string[]): Promise<FolderEntry[]> {
  const payload: EntriesPollRequest = { entries_refs: entriesRefs }
  const { data } = await http.post<GetEntriesResponse>('/users/entries', payload)
  return data.entries || []
}

export async function deleteEntry(entryId: string): Promise<void> {
  await http.delete(`/users/entries/${entryId}`)
}

export async function listFolders(): Promise<ListLibraryFoldersResponse> {
  const { data } = await http.get<ListLibraryFoldersResponse>('/users/folders')
  return {
    folders: data.folders || [],
    unfiled_count: data.unfiled_count || 0,
  }
}

export async function createFolder(name: string): Promise<LibraryFolder> {
  const { data } = await http.post<LibraryFolder>('/users/folders', { name })
  return data
}

export async function renameFolder(folderId: string, name: string): Promise<LibraryFolder> {
  const { data } = await http.patch<LibraryFolder>(`/users/folders/${folderId}`, { name })
  return data
}

export async function deleteFolder(folderId: string): Promise<void> {
  await http.delete(`/users/folders/${folderId}`)
}

export async function patchEntry(
  entryId: string,
  payload: { name?: string; library_folder_id?: string | null },
): Promise<FolderEntry> {
  const { data } = await http.patch<FolderEntry>(`/users/entries/${entryId}`, payload)
  return data
}

export async function moveEntries(
  entryIds: string[],
  libraryFolderId: string | null,
): Promise<BulkEntriesResponse> {
  const { data } = await http.post<BulkEntriesResponse>('/users/entries/move', {
    entry_ids: entryIds,
    library_folder_id: libraryFolderId,
  })
  return data
}

export async function deleteEntries(entryIds: string[]): Promise<BulkEntriesResponse> {
  const { data } = await http.post<BulkEntriesResponse>('/users/entries/delete', {
    entry_ids: entryIds,
  })
  return data
}
