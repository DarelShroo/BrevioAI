import { ref, computed, h, defineComponent} from 'vue';
import { AppstoreOutlined, SettingOutlined } from '@ant-design/icons-vue';
import { useMenuBravioStore, MenuBravioKeys, TextToolBoxKeys, ConfigurationKeys, selectedKeysNames } from '@/stores/useMenuBravioStore';
import OpenAiIcon from '@/assets/images/openai-icon.svg';
import LanguageIcon from '@/assets/images/language-icon2.svg';
import { notification } from 'ant-design-vue'

export default defineComponent({
    setup() {
        const theme = ref('dark');
        const menuBravioStore = useMenuBravioStore();
        
        const selectedKeysArray = computed(() => [
          menuBravioStore.selectedKeys.textToolBox,
          menuBravioStore.selectedKeys.configuration,
        ].filter(Boolean));
        
        
        function handleSelectedKeys(keys: string[]) {
          keys.forEach(key => {
            if (key.startsWith('text-tool-box')) {
              menuBravioStore.selectedKeys.textToolBox = key;
            } else if (key.startsWith('configuration')) {
              menuBravioStore.selectedKeys.configuration = key;
            }
          });
        }
        
        const openNotificationWithIcon = () => {
            notification['info']({
              message: 'Tool Box',
              description:
                `${selectedKeysNames[menuBravioStore.combinedSelectedKeys[0]]} selected`,
              placement: 'topRight'
          } );
        }
        
        const items = ref([
          {
            key: 'text-tool-box',
            icon: () => h(AppstoreOutlined),
            label: 'Text Tool Box',
            children: [
              {
                key: TextToolBoxKeys.textToolBoxToSummary,
                label: 'Audio Summary',
                onClick: () => {
                  menuBravioStore.toggleSelectKey(TextToolBoxKeys.textToolBoxToSummary, MenuBravioKeys.textToolBox)
                  openNotificationWithIcon()
                },
              },
              {
                key: TextToolBoxKeys.textToolBoxToTranscription,
                label: 'Audio Transcription',
                onClick: () => {
                  menuBravioStore.toggleSelectKey(TextToolBoxKeys.textToolBoxToTranscription, MenuBravioKeys.textToolBox)
                  openNotificationWithIcon()
                },
              },
              {
                key: TextToolBoxKeys.textToolBoxToDocFile,
                label: 'To Doc File',
                onClick: () =>{
                  menuBravioStore.toggleSelectKey(TextToolBoxKeys.textToolBoxToDocFile, MenuBravioKeys.textToolBox)
                  openNotificationWithIcon()
                },
              },
            ],
          },
          {
            key: 'configuration',
            icon: () => h(SettingOutlined),
            label: 'Configuration',
            children: [
              {
                key: ConfigurationKeys.configurationLanguage,
                icon: () =>
                  h('img', {
                    src: LanguageIcon,
                    alt: 'Language',
                    style: { width: '24px', height: '24px' },
                  }),
                label: 'Language',
                onClick: () => menuBravioStore.toggleSelectKey(ConfigurationKeys.configurationLanguage, MenuBravioKeys.configuration),
              },
              {
                key: ConfigurationKeys.configurationModel,
                icon: () =>
                  h('img', {
                    src: OpenAiIcon,
                    alt: 'GPT Model',
                    style: { width: '24px', height: '24px' },
                  }),
                label: 'GPT Model',
                onClick: () => menuBravioStore.toggleSelectKey(ConfigurationKeys.configurationModel, MenuBravioKeys.configuration),
              },
            ],
          },
        ]);
        return {
            theme,
            selectedKeysArray,
            handleSelectedKeys,
            items,
            menuBravioStore
        }
    }
})
