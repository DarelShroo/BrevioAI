import { describe, expect, it } from 'vitest'
import { i18nMessages } from '@/i18n'
import { UI_LOCALES } from '@/i18n/languages'

describe('plans i18n', () => {
  it('defines plans messages for every locale', () => {
    for (const locale of UI_LOCALES) {
      const messages = i18nMessages[locale]
      expect(messages.nav.plans).toBeTruthy()
      expect(messages.pages.plans).toBeTruthy()
      expect(messages.plans.title).toBeTruthy()
      expect(messages.plans.guestNotice).toBeTruthy()
      expect(messages.plans.compare.credits).toBeTruthy()
      expect(messages.plans.compare.rollover).toBeTruthy()
      expect(messages.plans.compare.bytesPerAudio).toBeTruthy()
      expect(messages.plans.compare.bytesPerVideo).toBeTruthy()
      expect(messages.plans.benefitRollover).toBeTruthy()
      expect(messages.plans.benefitPagesPeriod).toBeTruthy()
      expect(messages.plans.benefitDocSize).toBeTruthy()
      expect(messages.plans.benefitAudioSize).toBeTruthy()
      expect(messages.plans.benefitVideoSize).toBeTruthy()
      expect(messages.plans.benefitConcurrent).toBeTruthy()
      expect(messages.plans.checkoutUnavailable).toBeTruthy()
    }
  })
})
