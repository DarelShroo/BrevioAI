import { config } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { i18n } from '@/i18n'
import { DEFAULT_LOCALE } from '@/i18n/languages'

i18n.global.locale.value = DEFAULT_LOCALE
const pinia = createPinia()
setActivePinia(pinia)
config.global.plugins.push(i18n, pinia)
