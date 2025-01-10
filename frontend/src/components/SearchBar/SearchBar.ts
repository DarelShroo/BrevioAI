import { useStoreDeviceType } from '@/composables/useStoreDeviceType'
import { useStoreNotification } from '@/composables/useStoreNotification'
import { LanguageType } from '@/enums/language.enum'
import { api } from '@/utils/api'
import { ref, defineComponent, nextTick } from 'vue'

export default defineComponent({
  props: {
    loading: {
      type: Boolean,
      required: true,
    },
    isUserSearched: {
      type: Boolean,
      required: true,
    },
    error: {
      type: Boolean,
      required: true
    },
    result_content: {
      type: String,
      required: true
    }
  },
  emits: ['update:loading', 'update:isUserSearched', 'update:error', 'update:result_content'],
  setup(props, { emit }) {
    const searchValue = ref('')
    const onSearch = async () => {
        try {
          if(searchValue.value.length > 0){
            emit('update:loading', true);
            emit('update:isUserSearched', true);
            const result = await api().post('http://localhost:8000/brevio', {
              url: searchValue.value,
              language: LanguageType.SPANISH,
            });
            emit('update:result_content', result['summary_result'][0]);
            return 
          }else {
            throw new Error('URL parameter is empty');
          }          
        } catch (error: any) {
            const notification = useStoreNotification()
            const {placement} = useStoreDeviceType()
            notification.configNotification('error', '', error.message, placement.value)
            nextTick(() => {
              emit('update:error', true);
            });
        } finally {
          nextTick(() => {
            if(props.error){
              emit('update:isUserSearched', false);
            }
            emit('update:loading', false);
          });
        }
      };

    return {
      searchValue,
      onSearch,
    }
  },
})
