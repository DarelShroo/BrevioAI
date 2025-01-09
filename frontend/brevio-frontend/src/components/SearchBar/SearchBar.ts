import { ref, defineComponent } from 'vue'


export default defineComponent({
    setup() {
        const value = ref('')
        const onSearch = (value: string) => console.log(value)

        return {
            value, 
            onSearch
        }
    },
})
