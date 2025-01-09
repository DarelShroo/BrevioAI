import { defineComponent } from "vue";
import backgroundImage from '@/assets/images/ia-transformed.jpeg';
import { useMenuBravioStore, selectedKeysNames } from '@/stores/useMenuBravioStore';

export default defineComponent({
    setup() {
        const useMenuBravio = useMenuBravioStore();

        return {
            backgroundImage,
            selectedKeysNames,
            useMenuBravio
        }
    },
})