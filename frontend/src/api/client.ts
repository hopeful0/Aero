import axios, { type AxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/auth'

export const apiClient = axios.create({
  baseURL: '/api/v1',
  withCredentials: true,
  timeout: 30000,
  paramsSerializer: {
    serialize: (params: Record<string, unknown>) => {
      const sp = new URLSearchParams()
      for (const [key, value] of Object.entries(params)) {
        if (value === undefined || value === null) continue
        if (Array.isArray(value)) {
          for (const item of value) sp.append(key, String(item))
        } else if (typeof value === 'boolean') {
          sp.append(key, value ? 'true' : 'false')
        } else {
          sp.append(key, String(value))
        }
      }
      return sp.toString()
    },
  },
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

export const http = {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return apiClient.get(url, config) as unknown as Promise<T>
  },
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return apiClient.post(url, data, config) as unknown as Promise<T>
  },
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return apiClient.put(url, data, config) as unknown as Promise<T>
  },
  patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return apiClient.patch(url, data, config) as unknown as Promise<T>
  },
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return apiClient.delete(url, config) as unknown as Promise<T>
  },
}
