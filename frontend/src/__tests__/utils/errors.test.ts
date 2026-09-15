import { describe, expect, it } from 'vitest'
import { ApiError } from '@/types/api'
import { extractDetail, parseApiError } from '@/utils/errors'

describe('parseApiError', () => {
  it('reads string detail from ApiError body', () => {
    const err = new ApiError('fallback', 400, { detail: 'Bad request' })
    expect(parseApiError(err)).toBe('Bad request')
  })

  it('joins validation detail arrays', () => {
    expect(
      extractDetail({
        detail: [{ msg: 'too short' }, { msg: 'invalid' }],
      }),
    ).toBe('too short; invalid')
  })

  it('maps backend error codes through i18n', () => {
    const err = new ApiError('FOLDER_NAME_DUPLICATE', 409, { code: 'FOLDER_NAME_DUPLICATE' })
    expect(parseApiError(err)).toContain('already have a folder')
  })

  it('maps media transcription codes through i18n', () => {
    const err = new ApiError('MEDIA_FORMAT_NOT_ALLOWED', 415, { code: 'MEDIA_FORMAT_NOT_ALLOWED' })
    expect(parseApiError(err)).toContain('MP3')
  })

  it('handles missing response as backend unavailable', () => {
    const axiosLike = {
      isAxiosError: true,
      message: 'Network Error',
      response: undefined,
    }
    expect(parseApiError(axiosLike)).toContain('Backend unavailable')
  })
})
