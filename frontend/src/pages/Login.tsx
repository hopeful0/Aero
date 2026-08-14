import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useLogin, useRegisterHuman } from '@/api/hooks'
import { useAuthStore } from '@/store/auth'
import { ApiError } from '@/api/client'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const setHuman = useAuthStore((s) => s.setHuman)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const loginMut = useLogin()
  const registerMut = useRegisterHuman()

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      if (mode === 'login') {
        const res = await loginMut.mutateAsync({ email, password })
        setHuman({ humanId: res.human_id, name: res.name ?? email })
      } else {
        await registerMut.mutateAsync({ name, email, password })
        const res = await loginMut.mutateAsync({ email, password })
        setHuman({ humanId: res.human_id, name: res.name ?? email })
      }
      const next =
        (location.state as { from?: string } | null)?.from ?? '/'
      navigate(next, { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('登录失败')
      }
    }
  }

  const loading = loginMut.isPending || registerMut.isPending

  return (
    <section className="page login-page">
      <h1>{mode === 'login' ? '登录' : '注册新账号'}</h1>
      <form className="login-form" onSubmit={onSubmit}>
        {mode === 'register' && (
          <label className="field">
            <span>姓名</span>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
        )}
        <label className="field">
          <span>邮箱</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="field">
          <span>密码</span>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error ? <p className="form-error">{error}</p> : null}
        <button type="submit" className="btn btn--primary" disabled={loading}>
          {loading ? '处理中…' : mode === 'login' ? '登录' : '注册并登录'}
        </button>
        <button
          type="button"
          className="btn btn--ghost"
          onClick={() => {
            setError(null)
            setMode(mode === 'login' ? 'register' : 'login')
          }}
        >
          {mode === 'login' ? '没有账号？去注册' : '已有账号？去登录'}
        </button>
      </form>
    </section>
  )
}
