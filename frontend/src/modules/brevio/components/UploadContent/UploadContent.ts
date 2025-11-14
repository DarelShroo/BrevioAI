import { defineComponent, ref } from 'vue';
import { InboxOutlined } from '@ant-design/icons-vue';
import type { UploadFile } from 'ant-design-vue/es/upload/interface';
import type { UploadChangeParam } from 'ant-design-vue';

export default defineComponent({
  name: 'UploadContentView',
  components: { InboxOutlined },
  props: {
    summaryExtensions: {
      type: String,
      required: true
    }
  },
  setup(props, { emit }) {
    const fileList = ref<UploadFile[]>([]);

    const handleChange = (info: UploadChangeParam) => {
      fileList.value = info.fileList.map((file) => ({
        ...file,
        uid: file.uid || `${Date.now()}-${Math.random()}`,
        name: file.name || (file.file ? file.file.name : 'unknown'),
        status: file.status || 'uploading',
      }));
      fileList.value = [...fileList.value]; // Forza reactividad
      console.log('Updated fileList:', JSON.stringify(fileList.value, null, 2));
      updateFileList(fileList.value);
    };

    const handleDrop = (e: DragEvent) => {
      const files = e.dataTransfer?.files;
      console.log('Files dropped:', files);
      if (files) {
        Array.from(files).forEach((file) => {
          console.log('Dropped file:', file.name, file.type, file.size);
        });
      }
    };

    const dummyRequest = ({ file, onSuccess }: any) => {
      console.log('Processing file:', file.name);
      setTimeout(() => {
        onSuccess({ status: 'Minimodonedone' }, file);
        console.log('File marked as done:', file.name);
      }, 200);
    };

    const updateFileList = (newFileList: UploadFile[]) => {
      emit('update-file-list', newFileList);
    }

    return {
      fileList,
      handleChange,
      handleDrop,
      dummyRequest
    };
  },
});
