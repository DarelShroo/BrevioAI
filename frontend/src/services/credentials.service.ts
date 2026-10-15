import { http } from '@/services/http'
import { i18n } from '@/i18n'
import type {
  CredentialCreateRequest,
  CredentialUpdateRequest,
  UserCredential,
} from '@/types/user'

function asCredential(item: UserCredential): UserCredential {
  return {
    ...item,
    id: item.id || item._id || '',
    name: (item.name || '').trim(),
  }
}

export function credentialId(item: Pick<UserCredential, 'id' | '_id'> | string | null | undefined): string {
  if (!item) return ''
  if (typeof item === 'string') return item.trim()
  return (item.id || item._id || '').trim()
}

export function credentialDisplayName(
  item: Pick<UserCredential, 'name' | 'id' | '_id'> | null | undefined,
  fallback?: string,
): string {
  const resolvedFallback = fallback || String(i18n.global.t('profile.unnamedCredential'))
  if (!item) return resolvedFallback
  const name = (item.name || '').trim()
  if (name) return name
  const id = credentialId(item)
  return id ? `${resolvedFallback} (${id.slice(0, 8)})` : resolvedFallback
}

export async function listAllCredentials(): Promise<UserCredential[]> {
  const { data } = await http.get<UserCredential[]>('/user-credentials')
  return (data || []).map(asCredential)
}

export async function listCredentials(provider: string): Promise<UserCredential[]> {
  const { data } = await http.get<UserCredential[]>(`/user-credentials/${provider}`)
  return (data || []).map(asCredential)
}

export async function createCredential(
  payload: CredentialCreateRequest,
): Promise<UserCredential> {
  const { data } = await http.post<UserCredential>('/user-credentials', payload)
  return asCredential(data)
}

export async function setDefaultCredential(id: string): Promise<UserCredential> {
  const credentialIdValue = credentialId(id)
  if (!credentialIdValue) {
    throw new Error(i18n.global.t('errors.codes.CREDENTIAL_ID_INVALID'))
  }
  const { data } = await http.post<UserCredential>(
    `/user-credentials/${encodeURIComponent(credentialIdValue)}/default`,
  )
  return asCredential(data)
}

export async function renameCredential(
  id: string,
  payload: CredentialUpdateRequest,
): Promise<UserCredential> {
  const credentialIdValue = credentialId(id)
  if (!credentialIdValue) {
    throw new Error(i18n.global.t('errors.codes.CREDENTIAL_ID_INVALID'))
  }
  const { data } = await http.patch<UserCredential>(
    `/user-credentials/${encodeURIComponent(credentialIdValue)}`,
    payload,
  )
  return asCredential(data)
}

export async function deleteCredential(id: string): Promise<void> {
  const credentialIdValue = credentialId(id)
  if (!credentialIdValue) {
    throw new Error(i18n.global.t('errors.codes.CREDENTIAL_ID_INVALID'))
  }
  await http.delete(`/user-credentials/${encodeURIComponent(credentialIdValue)}`)
}
