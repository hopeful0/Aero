import axios from 'axios'
import { useAuthStore } from '@/store/auth'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  timeout: 30000,
})

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly details: unknown
  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

apiClient.interceptors.response.use(
  (response) => {
    const body = response.data
    return body && typeof body === 'object' && 'data' in body ? body.data : body
  },
  (error) => {
    const status = error?.response?.status ?? 0
    const errObj = error?.response?.data?.error
    return Promise.reject(
      new ApiError(
        errObj?.code ?? 'UNKNOWN',
        errObj?.message ?? error?.message ?? 'Request failed',
        status,
        errObj?.details,
      ),
    )
  },
)
