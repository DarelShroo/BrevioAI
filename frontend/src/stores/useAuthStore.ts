import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
  }),

  getters: {
    userLoggedIn(state): boolean {
      if (!state.token) return false

      try {
        const payload = JSON.parse(atob(state.token.split('.')[1]))
        console.log(payload)
        const expiry = payload.exp
        return Date.now() < expiry * 1000
      } catch (error) {
        console.error('Token inválido:', error)
        return false
      }
    },
  },

  actions: {
    setToken(token: string) {
      this.token = token
      localStorage.setItem('token', token)
    },
    getToken(){
      return this.token
    },
    logout() {
      this.token = null
      localStorage.removeItem('token')
      import('@/router').then(({ default: router }) => {
        router.push({name: 'home'})
      })
    },
  },
})
