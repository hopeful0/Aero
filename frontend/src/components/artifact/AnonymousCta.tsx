import { Link } from 'react-router-dom'

interface AnonymousCtaProps {
  next: string
}

export default function AnonymousCta({ next }: AnonymousCtaProps) {
  return (
    <div className="anon-cta">
      <p className="muted">
        这是公开产物，任何人可读。想提交反馈或查看血统树？
      </p>
      <Link className="btn btn--primary" to="/login" state={{ from: next }}>
        登录后反馈与看血统
      </Link>
    </div>
  )
}
