import { describe, expect, it } from 'vitest'
import {
  canDownloadEntry,
  detectFileKind,
  entryCreatedAt,
  entryDurationSeconds,
  entryErrorMessage,
  entryFileKind,
  entryPrimaryName,
  entrySourceLabel,
  entryStatus,
  fileKindIcon,
  formatDuration,
  normalizeStatus,
  uniqueDownloadResultIndex,
} from '@/utils/entries'
import type { FolderEntry } from '@/types/user'

describe('entries helpers', () => {
  it('normalizes legacy completed results', () => {
    expect(normalizeStatus({ download_location: 'data/x' })).toBe('COMPLETED')
    expect(normalizeStatus({ success: false })).toBe('FAILED')
  })

  it('aggregates entry status', () => {
    const entry: FolderEntry = {
      user_id: 'u1',
      name: 'Job',
      results: [{ status: 'PROCESSING' }, { status: 'COMPLETED' }],
    }
    expect(entryStatus(entry)).toBe('PROCESSING')
    entry.results = [{ status: 'COMPLETED' }, { status: 'COMPLETED' }]
    expect(entryStatus(entry)).toBe('COMPLETED')
    entry.results = [{ status: 'FAILED' }, { status: 'COMPLETED' }]
    expect(entryStatus(entry)).toBe('FAILED')
    entry.results = [{ status: 'PROCESSING', phase: 'TRANSCRIBING' }]
    expect(entryStatus(entry)).toBe('TRANSCRIBING')
  })

  it('detects file kinds and icons', () => {
    expect(detectFileKind('report.PDF')).toBe('pdf')
    expect(detectFileKind('notes.docx')).toBe('docx')
    expect(detectFileKind('talk.mp3')).toBe('audio')
    expect(detectFileKind('clip.mp4')).toBe('video')
    expect(fileKindIcon('pdf')).toContain('file-pdf')
  })

  it('keeps custom entry names independent from contained files', () => {
    const entry: FolderEntry = {
      id: 'abcdef123456',
      user_id: 'u1',
      name: 'Mi carpeta',
      results: [
        { name: 'chapter.pdf', status: 'COMPLETED' },
        { name: 'appendix.pdf', status: 'COMPLETED' },
      ],
    }
    expect(entryPrimaryName(entry)).toBe('Mi carpeta')

    entry.results = [{ name: 'appendix.pdf', status: 'COMPLETED' }]
    expect(entryPrimaryName(entry)).toBe('Mi carpeta')

    entry.results = [
      { name: 'renamed-first.pdf', status: 'COMPLETED' },
      { name: 'appendix.pdf', status: 'COMPLETED' },
    ]
    expect(entryPrimaryName(entry)).toBe('Mi carpeta')

    entry.results = [
      { name: 'appendix.pdf', status: 'COMPLETED' },
      { name: 'chapter.pdf', status: 'COMPLETED' },
    ]
    expect(entryPrimaryName(entry)).toBe('Mi carpeta')
  })

  it('never derives the entry title from files[0]', () => {
    expect(
      entryPrimaryName({
        id: 'abcdef123456',
        user_id: 'u1',
        name: '',
        results: [
          { name: 'chapter.pdf' },
          { name: 'appendix.pdf' },
        ],
      }),
    ).toBe('Summary 123456')

    expect(
      entryPrimaryName({
        id: 'abcdef123456',
        user_id: 'u1',
        name: 'chapter.pdf',
        original_name: 'chapter.pdf; appendix.pdf',
        results: [
          { name: 'chapter.pdf' },
          { name: 'appendix.pdf' },
        ],
      }),
    ).toBe('Summary 123456')

    expect(
      entryPrimaryName({
        id: 'abcdef123456',
        user_id: 'u1',
        name: 'chapter.pdf (+1)',
        results: [
          { name: 'chapter.pdf' },
          { name: 'appendix.pdf' },
        ],
      }),
    ).toBe('Summary 123456')
  })

  it('uses a stable id fallback when the entry has no custom name', () => {
    expect(
      entryPrimaryName({
        id: 'abcdef123456',
        user_id: 'u1',
        name: '',
        results: [],
      }),
    ).toBe('Summary 123456')
    expect(
      entryPrimaryName({
        id: 'abcdef123456',
        user_id: 'u1',
        name: 'Document 0',
        results: [{ name: 'Document 0' }],
      }),
    ).toBe('Summary 123456')
  })

  it('allows download when at least one result is completed', () => {
    const multi: FolderEntry = {
      id: 'e1',
      user_id: 'u1',
      name: 'Mi carpeta',
      results: [
        { name: 'a.pdf', status: 'COMPLETED', index: 0 },
        { name: 'b.pdf', status: 'COMPLETED', index: 1 },
      ],
    }
    expect(canDownloadEntry(multi)).toBe(true)
    expect(uniqueDownloadResultIndex(multi)).toBeNull()

    const single: FolderEntry = {
      id: 'e2',
      user_id: 'u1',
      name: 'Uno',
      results: [{ name: 'only.pdf', status: 'COMPLETED', index: 0 }],
    }
    expect(canDownloadEntry(single)).toBe(true)
    expect(uniqueDownloadResultIndex(single)).toBe(0)

    const oneOfMany: FolderEntry = {
      id: 'e3',
      user_id: 'u1',
      name: 'Parcial',
      results: [
        { name: 'a.pdf', status: 'FAILED', index: 0 },
        { name: 'b.pdf', status: 'COMPLETED', index: 1 },
      ],
    }
    expect(canDownloadEntry(oneOfMany)).toBe(true)
    expect(uniqueDownloadResultIndex(oneOfMany)).toBe(1)

    const noneReady: FolderEntry = {
      id: 'e4',
      user_id: 'u1',
      name: 'Pendiente',
      results: [
        { name: 'a.pdf', status: 'PROCESSING', index: 0 },
        { name: 'b.pdf', status: 'FAILED', index: 1 },
      ],
    }
    expect(canDownloadEntry(noneReady)).toBe(false)
    expect(uniqueDownloadResultIndex(noneReady)).toBeNull()
  })

  it('reads metadata helpers and truncates errors', () => {
    const entry: FolderEntry = {
      id: '507f1f77bcf86cd799439011',
      user_id: 'u1',
      name: 'Job',
      source_type: 'documents',
      created_at: '2026-01-02T10:00:00Z',
      results: [{ status: 'FAILED', error_message: 'x'.repeat(200) }],
    }
    expect(entrySourceLabel(entry)).toBe('Documents')
    expect(entryCreatedAt(entry)?.toISOString()).toContain('2026-01-02')
    expect(entryErrorMessage(entry)?.endsWith('…')).toBe(true)
    expect(
      entryErrorMessage({
        user_id: 'u1',
        name: 'Job',
        results: [{ status: 'FAILED', error_code: 'MEDIA_NO_AUDIO_TRACK' }],
      }),
    ).toContain('audio')
    expect(entryFileKind(entry)).toBe('file')
    expect(entryDurationSeconds({ user_id: 'u1', name: 'x', results: [{ duration: 12 }, { duration: 8 }] })).toBe(20)
    expect(formatDuration(20)).toBe('20s')
    expect(formatDuration(75)).toBe('1m 15s')
  })
})
