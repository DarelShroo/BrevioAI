import { describe, expect, it } from 'vitest'
import {
  isDocumentFile,
  isMediaFile,
  isValidEmail,
  isYoutubeUrl,
  validatePassword,
  validateUsername,
} from '@/utils/validation'

describe('validation', () => {
  it('validates username length', () => {
    expect(validateUsername('abc')).toBeTruthy()
    expect(validateUsername('abcdef')).toBeNull()
  })

  it('validates strong passwords', () => {
    expect(validatePassword('weak')).toBeTruthy()
    expect(validatePassword('Aa1@aaaa')).toBeNull()
  })

    it('checks emails and file types', () => {
    expect(isValidEmail('a@b.com')).toBe(true)
    expect(isDocumentFile(new File(['x'], 'a.pdf'))).toBe(true)
    expect(isDocumentFile(new File(['x'], 'a.txt'))).toBe(false)
    expect(isMediaFile(new File(['x'], 'a.mp3'))).toBe(true)
    expect(isMediaFile(new File(['x'], 'a.m4a'))).toBe(true)
    expect(isMediaFile(new File(['x'], 'a.wav'))).toBe(true)
    expect(isMediaFile(new File(['x'], 'a.mp4'))).toBe(true)
    expect(isMediaFile(new File(['x'], 'a.avi'))).toBe(false)
    expect(isMediaFile(new File(['x'], 'a.mov'))).toBe(false)
    expect(isMediaFile(new File(['x'], 'a.mkv'))).toBe(false)
    expect(isMediaFile(new File(['x'], 'a.webm'))).toBe(false)
    expect(isYoutubeUrl('https://www.youtube.com/watch?v=1')).toBe(true)
    expect(isYoutubeUrl('https://example.com')).toBe(false)
  })
})
