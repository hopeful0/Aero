import * as Dialog from '@radix-ui/react-dialog'

interface DrawerProps {
  triggerLabel?: string
  title: string
  description?: string
  children?: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export default function Drawer({
  triggerLabel,
  title,
  description,
  children,
  open,
  onOpenChange,
}: DrawerProps) {
  const trigger = triggerLabel ? (
    <Dialog.Trigger asChild>
      <button className="drawer__trigger">{triggerLabel}</button>
    </Dialog.Trigger>
  ) : null
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      {trigger}
      <Dialog.Portal>
        <Dialog.Overlay className="drawer__overlay" />
        <Dialog.Content className="drawer__content" aria-label={title}>
          <div className="drawer__header">
            <Dialog.Title className="drawer__title">{title}</Dialog.Title>
            {description ? (
              <Dialog.Description className="drawer__desc">
                {description}
              </Dialog.Description>
            ) : null}
          </div>
          <div className="drawer__body">{children}</div>
          <div className="drawer__footer">
            <Dialog.Close className="drawer__close" aria-label="close">
              关闭
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
