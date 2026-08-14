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
  clear: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      human: null,
      setAuth: (token, human) => set({ token, human }),
      clear: () => set({ token: null, human: null }),
    }),
    { name: 'aero-auth' },
  ),
)
