import { notification, type UploadFile } from 'ant-design-vue';
import { computed, defineComponent, ref } from 'vue';
import { AppstoreOutlined } from '@ant-design/icons-vue';
import { useMenuBravioStore } from '../../../../stores/useMenuBravioStore';
import { selectedKeysNames } from '../../constants/selected-keys-name.constants';
import { ConfigurationKeys } from '../../enums/configuration-keys.enum';
import { MenuBravioKeys } from '../../enums/menu-bravio-keys';
import { TextToolBoxKeys } from '../../enums/text-tool-box-keys.enum';
import UploadContentView from './../UploadContent/UploadContentView.vue';
import FormContent from '../FormContent/FormContentView.vue';

export default defineComponent({
  name: 'MenuBar',
  components: { AppstoreOutlined, UploadContentView, FormContent },
  setup() {
    const theme = ref('dark');
    const menuBravioStore = useMenuBravioStore();

    const fileList = ref<UploadFile[]>([]);

    const summaryDocumentsExtension = ref('.pdf,.docx');
    const summaryMediaExtension = ref('.mp4,.mp3');

    const selectedKeysArray = computed(() =>
      [
        menuBravioStore.selectedKeys.textToolBox,
        menuBravioStore.selectedKeys.configuration,
      ].filter(Boolean),
    );

    const handleOpenKeys = (keys: string[]) => {
      menuBravioStore.openKeys = keys.length > 0 ? [keys[keys.length - 1]] : [];
    };

    function handleSelectedKeys(keys: string[]) {
      console.log('Selected keys:', keys);
      keys.forEach((key) => {
        if (key.startsWith('text-tool-box')) {
          menuBravioStore.selectedKeys.textToolBox = key;
        } else if (key.startsWith('configuration')) {
          menuBravioStore.selectedKeys.configuration = key;
        }
      });
    }

    // Formularios reactivos
    const youtubeUrl = ref('');
    const mediaInput = ref('');
    const documentInput = ref('');

    // Acciones de envío
    function submitYoutube() {
      console.log('Procesando YouTube:', youtubeUrl.value);
      menuBravioStore.toggleSelectKey(
        TextToolBoxKeys.textToolBoxSummaryYoutube,
        MenuBravioKeys.textToolBox,
      );
    }

    function submitMedia() {
      console.log('Procesando media:', mediaInput.value);
      menuBravioStore.toggleSelectKey(
        TextToolBoxKeys.textToolBoxSummaryMedia,
        MenuBravioKeys.textToolBox,
      );
    }

    function submitDocument() {
      console.log('Procesando documento:', documentInput.value);
      menuBravioStore.toggleSelectKey(
        TextToolBoxKeys.textToolBoxSummaryDocument,
        MenuBravioKeys.textToolBox,
      );
    }

    const activeKey = ref('1');

    const updateFileList = (newFileList: UploadFile[]) => {
      fileList.value = newFileList;
      console.log('Updated in MenuBar:', JSON.stringify(fileList.value, null, 2));
    }

    return {
      theme,
      selectedKeysArray,
      handleSelectedKeys,
      handleOpenKeys,
      menuBravioStore,
      submitYoutube,
      submitMedia,
      submitDocument,
      activeKey,
      mediaInput,
      documentInput,
      summaryDocumentsExtension,
      summaryMediaExtension,
      updateFileList,
      fileList
    };
  },
});
