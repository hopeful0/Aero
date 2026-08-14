import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface HumanInfo {
  humanId: string
  name: string
}

interface AuthState {
  token: string | null
  human: HumanInfo | null
  setAuth: (token: string, human: HumanInfo) => void
  setHuman: (human: HumanInfo) => void
  setToken: (token: string | null) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      human: null,
      setAuth: (token, human) => set({ token, human }),
      setHuman: (human) => set({ human }),
      setToken: (token) => set({ token }),
      clear: () => set({ token: null, human: null }),
    }),
    { name: 'aero-auth' },
  ),
)
