import { i18n } from '@/i18n'

export function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

export function validateUsername(username: string): string | null {
  const value = username.trim()
  if (value.length < 6 || value.length > 25) {
    return i18n.global.t('validation.usernameLength')
  }
  return null
}

export function validatePassword(password: string): string | null {
  if (password.length < 8) {
    return i18n.global.t('validation.passwordLength')
  }
  if (!/[A-Z]/.test(password)) {
    return i18n.global.t('validation.passwordUppercase')
  }
  if (!/[a-z]/.test(password)) {
    return i18n.global.t('validation.passwordLowercase')
  }
  if (!/\d/.test(password)) {
    return i18n.global.t('validation.passwordDigit')
  }
  if (!/[\W_]/.test(password)) {
    return i18n.global.t('validation.passwordSpecial')
  }
  return null
}

export function validateIdentity(identity: string): string | null {
  const value = identity.trim()
  if (!value) return i18n.global.t('validation.identityRequired')
  if (isValidEmail(value)) return null
  if (!/^[a-zA-Z0-9_.-]{3,25}$/.test(value)) {
    return i18n.global.t('validation.validIdentity')
  }
  return null
}

export const MEDIA_EXTENSIONS = ['.mp3', '.m4a', '.wav', '.mp4'] as const
export const REJECTED_MEDIA_EXTENSIONS = ['.avi', '.mov', '.mkv', '.webm'] as const

export function isDocumentFile(file: File): boolean {
  const name = file.name.toLowerCase()
  return name.endsWith('.pdf') || name.endsWith('.docx')
}

export function isMediaFile(file: File): boolean {
  const name = file.name.toLowerCase()
  return MEDIA_EXTENSIONS.some((ext) => name.endsWith(ext))
}

export function isYoutubeUrl(url: string): boolean {
  try {
    const parsed = new URL(url.trim())
    return (
      parsed.hostname.includes('youtube.com') ||
      parsed.hostname.includes('youtu.be') ||
      parsed.hostname.includes('youtube-nocookie.com')
    )
  } catch {
    return false
  }
}
