import { computed } from 'vue'

export const modelMessages = (selectedModel: string = 'GPT-4') => {
  const modelSelectedMessage = computed(() => {
    return `You have selected the ${selectedModel} GPT model. Now, let’s generate the text!`
  })

  const placeHolderSelectedModel = 'Select a Model'

  return {
    modelSelectedMessage,
    placeHolderSelectedModel
  }
}
