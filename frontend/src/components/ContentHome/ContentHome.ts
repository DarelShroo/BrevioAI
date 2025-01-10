import { defineComponent, h, ref } from 'vue'
import { Spin } from 'ant-design-vue'
import backgroundImage from '@/assets/images/ia-transformed.jpeg'
import { useMenuBravioStore, selectedKeysNames } from '@/stores/useMenuBravioStore'
export default defineComponent({
  setup() {
    const useMenuBravio = useMenuBravioStore()
    const loading = ref(false)
    const isUserSearched = ref(false)
    const error = ref(false)
    const result_content = ref('')
    Spin.setDefaultIndicator({
      indicator: h(
        'div',
        {
          class: 'ant-spin ant-spin-lg ant-spin-spinning',
          styles: 'color:  #303C3E',
        },
        [
          h('span', { class: 'ant-spin-dot ant-spin-dot-spin', style: '' }, [
            h('i', {
              class: 'ant-spin-dot-item',
              style:
                'background-color: #FFFFFF; color: #fff; top: -10px; inset-inline-start: 25px; transform: scale(2); border-radius: 0; cursor: none',
            }),
            h('i', {
              class: 'ant-spin-dot-item',
              style:
                'background-color: #FFFFFF; color: #fff; top: -10px; inset-inline-start: -10px; transform: scale(2); border-radius: 0; cursor: none',
            }),
            h('i', {
              class: 'ant-spin-dot-item',
              style:
                'background-color: #FFFFFF; color: #fff; bottom: -10px; inset-inline-start: -10px; transform: scale(2); border-radius: 0; cursor: none',
            }),
            h('i', {
              class: 'ant-spin-dot-item',
              style:
                'background-color: #FFFFFF; color: #fff; bottom: -10px; inset-inline-start: 25px; transform: scale(2); border-radius: 0; cursor: none',
            }),
          ]),
        ],
      ),
    })

    const handleLoadingUpdate = (newLoadingValue: any) => {
      loading.value = newLoadingValue
    }
    const handleisUserSearchedUpdate = (newisUserSearchedValue: any) => {
      loading.value = newisUserSearchedValue
    }
    const handleisErrorUpdate = (newIsHandleErrror: any) => {
      error.value = newIsHandleErrror
    }

    const handlResultContentUpdate = (newResultContent: any) => {
      const match = newResultContent.match(/summary=([\s\S]*?), message/);
      result_content.value = match[1].trim();
    }


    return {
      backgroundImage,
      selectedKeysNames,
      useMenuBravio,
      loading,
      isUserSearched,
      error,
      handleisUserSearchedUpdate,
      handleLoadingUpdate,
      handleisErrorUpdate,
      handlResultContentUpdate,
      result_content,
    }
  },
})
