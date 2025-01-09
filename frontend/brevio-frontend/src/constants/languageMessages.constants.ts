import { computed } from 'vue'

export const languageMessages = (selectedLanguage: string = 'English'): any => {
    const languageSelectedMessage = computed(() => {
      return `You’ve selected "${selectedLanguage}". Now, let’s translate the text to this language!`
    })
  
    const placeHolderSelectedLanguage = 'Select a Language'

    return {
      languageSelectedMessage,
      placeHolderSelectedLanguage
    }
  }
  