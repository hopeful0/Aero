interface VisibilityBadgeProps {
  visibility: 'private' | 'public'
  showPrivate?: boolean
}

export default function VisibilityBadge({
  visibility,
  showPrivate = false,
}: VisibilityBadgeProps) {
  if (visibility === 'public') {
    return (
      <span className="chip chip--vis chip--vis-public" aria-label="公开产物">
        公开
      </span>
    )
  }
  if (showPrivate) {
    return (
      <span className="chip chip--vis chip--vis-private" aria-label="私有产物">
        私有
      </span>
    )
  }
  return null
}
