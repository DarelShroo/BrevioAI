import { describe, expect, it } from 'vitest';
import { defineComponent, nextTick } from 'vue';
import { mount } from '@vue/test-utils';
import { useStoreDeviceType } from '@/modules/brevio/composables/useStoreDeviceType';

const ProbeComponent = defineComponent({
	setup() {
		const { isMobile, placement } = useStoreDeviceType();
		return { isMobile, placement };
	},
	template: '<div />',
});

describe('useStoreDeviceType', () => {
	it('returns desktop placement for wide screens', async () => {
		Object.defineProperty(window, 'innerWidth', { value: 1024, configurable: true });

		const wrapper = mount(ProbeComponent);
		await nextTick();

		expect(wrapper.vm.isMobile).toBe(false);
		expect(wrapper.vm.placement).toBe('topRight');
	});

	it('returns mobile placement for narrow screens', async () => {
		Object.defineProperty(window, 'innerWidth', { value: 375, configurable: true });

		const wrapper = mount(ProbeComponent);
		await nextTick();

		expect(wrapper.vm.isMobile).toBe(true);
		expect(wrapper.vm.placement).toBe('bottom');
	});
});
