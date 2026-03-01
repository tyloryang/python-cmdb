import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, refresh as apiRefresh, getMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('access_token') || '')
  const refreshToken = ref<string>(localStorage.getItem('refresh_token') || '')
  const user = ref<any>(null)

  async function login(username: string, password: string) {
    const data = await apiLogin(username, password)
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await fetchMe()
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function doRefreshToken() {
    try {
      const data = await apiRefresh(refreshToken.value)
      token.value = data.access_token
      refreshToken.value = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      return data.access_token
    } catch {
      logout()
      throw new Error('Token refresh failed')
    }
  }

  async function fetchMe() {
    try {
      user.value = await getMe()
    } catch {
      // ignore
    }
  }

  return { token, refreshToken, user, login, logout, doRefreshToken, fetchMe }
})
