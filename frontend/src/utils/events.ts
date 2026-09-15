export function jobIdFromToastClass(styleClass: unknown): string | null {
  const match = String(styleClass || '').match(/(?:^|\s)job-id-([A-Za-z0-9_-]+)/)
  return match?.[1] ?? null
}

export function jobEventToastClass(jobId: string): string {
  return `job-event-toast job-id-${jobId}`
}
