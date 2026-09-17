<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { List } from '@lucide/vue'
import { renderMarkdown, type TocItem } from '@/utils/markdown'
import '@/assets/styles/markdown-viewer.css'

const props = withDefaults(
  defineProps<{
    source: string
    loading?: boolean
    error?: string | null
    /** When false, TOC starts collapsed (toggle still available). */
    tocDefaultOpen?: boolean
  }>(),
  {
    loading: false,
    error: null,
    tocDefaultOpen: true,
  },
)

const { t } = useI18n()
const bodyEl = ref<HTMLElement | null>(null)
const progress = ref(0)
const tocOpen = ref(props.tocDefaultOpen)
const activeId = ref('')
const copyTimers = new WeakMap<HTMLButtonElement, ReturnType<typeof setTimeout>>()
let boundScrollEl: HTMLElement | null = null

const rendered = computed(() => renderMarkdown(props.source || ''))
const toc = computed<TocItem[]>(() => rendered.value.toc)
const showToc = computed(() => toc.value.length >= 1)

watch(
  () => props.tocDefaultOpen,
  (open) => {
    tocOpen.value = open
  },
)

function cssEscape(value: string): string {
  if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
    return CSS.escape(value)
  }
  return value.replace(/([^a-zA-Z0-9_-])/g, '\\$1')
}

function updateProgress() {
  const el = bodyEl.value
  if (!el) {
    progress.value = 0
    return
  }
  const max = el.scrollHeight - el.clientHeight
  if (max <= 1) {
    progress.value = 100
    return
  }
  progress.value = Math.min(100, Math.max(0, Math.round((el.scrollTop / max) * 100)))
}

function updateActiveHeading() {
  const el = bodyEl.value
  if (!el || !toc.value.length) {
    activeId.value = ''
    return
  }
  const headings = toc.value
    .map((item) => el.querySelector<HTMLElement>(`#${cssEscape(item.id)}`))
    .filter((node): node is HTMLElement => Boolean(node))

  let current = headings[0]?.id || ''
  const top = el.scrollTop + 48
  for (const heading of headings) {
    if (heading.offsetTop <= top) current = heading.id
    else break
  }
  activeId.value = current
}

function onScroll() {
  updateProgress()
  updateActiveHeading()
}

function bindScrollTarget(el: HTMLElement | null) {
  if (boundScrollEl === el) return
  if (boundScrollEl) {
    boundScrollEl.removeEventListener('scroll', onScroll)
  }
  boundScrollEl = el
  if (el) {
    el.addEventListener('scroll', onScroll, { passive: true })
    updateProgress()
    updateActiveHeading()
  }
}

async function scrollToHeading(id: string) {
  const el = bodyEl.value?.querySelector<HTMLElement>(`#${cssEscape(id)}`)
  if (!el || !bodyEl.value) return
  bodyEl.value.scrollTo({ top: Math.max(0, el.offsetTop - 12), behavior: 'smooth' })
  activeId.value = id
  history.replaceState(null, '', `#${id}`)
}

async function copyCode(button: HTMLButtonElement) {
  const block = button.closest('.md-code')
  const code = block?.querySelector('code')?.textContent || ''
  const copyLabel = button.dataset.copyLabel || t('markdown.copy')
  const copiedLabel = button.dataset.copiedLabel || t('markdown.copied')

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(code)
    } else {
      const ta = document.createElement('textarea')
      ta.value = code
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.left = '-9999px'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      ta.remove()
    }
    button.textContent = copiedLabel
    button.classList.add('is-copied')
    const prev = copyTimers.get(button)
    if (prev) clearTimeout(prev)
    copyTimers.set(
      button,
      setTimeout(() => {
        button.textContent = copyLabel
        button.classList.remove('is-copied')
      }, 1600),
    )
  } catch {
    button.textContent = copyLabel
  }
}

function onBodyClick(event: MouseEvent) {
  const target = event.target as HTMLElement | null
  if (!target) return

  const copyBtn = target.closest('button.md-code__copy') as HTMLButtonElement | null
  if (copyBtn) {
    event.preventDefault()
    void copyCode(copyBtn)
    return
  }

  const anchor = target.closest('a') as HTMLAnchorElement | null
  if (!anchor || !bodyEl.value?.contains(anchor)) return
  const href = anchor.getAttribute('href') || ''
  if (href.startsWith('#')) {
    event.preventDefault()
    void scrollToHeading(href.slice(1))
  }
}

function bindBrokenImages() {
  const el = bodyEl.value
  if (!el) return
  el.querySelectorAll<HTMLImageElement>('img.md-img').forEach((img) => {
    if (img.dataset.bound === '1') return
    img.dataset.bound = '1'
    img.addEventListener('error', () => {
      img.classList.add('md-img--broken')
      img.alt = img.alt || t('markdown.imageBroken')
      img.removeAttribute('src')
    })
  })
}

function localizeCopyButtons() {
  const el = bodyEl.value
  if (!el) return
  el.querySelectorAll<HTMLButtonElement>('button.md-code__copy').forEach((btn) => {
    btn.dataset.copyLabel = t('markdown.copy')
    btn.dataset.copiedLabel = t('markdown.copied')
    btn.setAttribute('aria-label', t('markdown.copyCode'))
    if (!btn.classList.contains('is-copied')) {
      btn.textContent = t('markdown.copy')
    }
  })
}

watch(bodyEl, (el) => {
  bindScrollTarget(el)
})

watch(
  () => rendered.value.html,
  async () => {
    await nextTick()
    bindScrollTarget(bodyEl.value)
    localizeCopyButtons()
    bindBrokenImages()
    updateProgress()
    updateActiveHeading()
  },
)

onBeforeUnmount(() => {
  bindScrollTarget(null)
})
</script>

<template>
  <div class="markdown-viewer" data-testid="markdown-viewer">
    <div
      class="md-progress"
      role="progressbar"
      :aria-valuenow="progress"
      aria-valuemin="0"
      aria-valuemax="100"
      :aria-label="t('markdown.readingProgress')"
    >
      <div class="md-progress__track">
        <div class="md-progress__bar" :style="{ width: `${progress}%` }" />
      </div>
      <span class="md-progress__label">{{ progress }}%</span>
    </div>

    <div v-if="loading" class="md-state" data-testid="markdown-loading">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="error" class="md-state md-state--error" data-testid="markdown-error">
      {{ error }}
    </div>
    <div v-else-if="!source.trim()" class="md-state" data-testid="markdown-empty">
      {{ t('markdown.empty') }}
    </div>

    <div
      v-else
      class="md-layout"
      :class="{
        'md-layout--with-toc': showToc,
        'md-layout--toc-open': showToc && tocOpen,
        'md-layout--toc-closed': showToc && !tocOpen,
      }"
    >
      <aside v-if="showToc" class="md-toc" data-testid="markdown-toc">
        <button
          type="button"
          class="md-toc__toggle"
          :aria-expanded="tocOpen"
          data-testid="markdown-toc-toggle"
          @click="tocOpen = !tocOpen"
        >
          <List :size="16" :stroke-width="2" aria-hidden="true" />
          <span>{{ tocOpen ? t('markdown.hideContents') : t('markdown.showContents') }}</span>
        </button>
        <nav
          v-show="tocOpen"
          class="md-toc__nav"
          :class="{ 'is-open': tocOpen }"
          :aria-label="t('markdown.contents')"
        >
          <ol>
            <li v-for="item in toc" :key="item.id" :data-level="item.level">
              <a
                :href="`#${item.id}`"
                :class="{ 'is-active': activeId === item.id }"
                @click.prevent="scrollToHeading(item.id)"
              >
                {{ item.text }}
              </a>
            </li>
          </ol>
        </nav>
      </aside>

      <article
        ref="bodyEl"
        class="md-body markdown-body"
        data-testid="markdown-body"
        tabindex="0"
        @click="onBodyClick"
        v-html="rendered.html"
      />
    </div>
  </div>
</template>
