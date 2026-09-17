import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import StatusBadge from '@/components/common/StatusBadge.vue'
import EstimatePanel from '@/components/summary/EstimatePanel.vue'
import type { EstimateDocumentsData } from '@/types/brevio'

describe('StatusBadge', () => {
  it('renders status text', () => {
    const wrapper = mount(StatusBadge, {
      props: { status: 'COMPLETED' },
    })
    expect(wrapper.text()).toContain('Completed')
  })
})

describe('EstimatePanel', () => {
  it('shows estimate summary', () => {
    const estimate: EstimateDocumentsData = {
      can_process: true,
      estimation: {
        input_tokens: {
          prompt_template: 1,
          documents_content: 2,
          structural: 0,
          total: 3,
        },
        output_tokens: { minimum: 1, expected: 5, max_ceiling: 10 },
        total_tokens_worst_case: 13,
      },
      documents: [],
      tokenization: { method: 'approx', confidence: 'low', estimated_error_margin: 0.1 },
      model: {
        name: 'gpt-4o-mini',
        provider: 'openai',
        context_limit: 128000,
        max_output_tokens: 4096,
        supports_chunking: true,
      },
      pricing: {
        model: 'gpt-4o-mini',
        provider_cost_currency: 'USD',
        platform_currency: 'USD',
        expected_cost: 0.01,
        max_cost: 0.02,
        pricing_version: '1',
      },
      credits: { expected: 1, maximum: 2 },
      chunking: { required: false, calls: 1 },
      estimation_id: 'e1',
      estimated_at: '2026-01-01T00:00:00Z',
      warnings: [],
    }

    const wrapper = mount(EstimatePanel, {
      props: { estimate },
      global: {
        stubs: {
          Message: { template: '<div><slot /></div>' },
        },
      },
    })
    expect(wrapper.text()).toContain('Ready to run')
    expect(wrapper.text()).toContain('3')
  })
})
