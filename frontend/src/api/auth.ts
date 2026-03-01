import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE

// Use a separate axios instance for auth (no token interceptor to avoid circular deps)
const authHttp = axios.create({ baseURL: BASE, timeout: 15000 })

export function login(username: string, password: string) {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)
  return authHttp
    .post<{ access_token: string; refresh_token: string }>('/v1/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    .then((r) => r.data)
}

export function refresh(refreshToken: string) {
  return authHttp
    .post<{ access_token: string; refresh_token: string }>(
      `/v1/auth/refresh?refresh_token=${encodeURIComponent(refreshToken)}`
    )
    .then((r) => r.data)
}

export function getMe() {
  const token = localStorage.getItem('access_token')
  return authHttp
    .get<any>('/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
    .then((r) => r.data)
}
