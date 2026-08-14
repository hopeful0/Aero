import * as Dialog from '@radix-ui/react-dialog'

export default function Drawer() {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button className="drawer__trigger">血统</button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="drawer__overlay" />
        <Dialog.Content
          className="drawer__content"
          aria-label="lineage drawer placeholder"
        >
          <div className="drawer__header">
            <Dialog.Title className="drawer__title">血统面板</Dialog.Title>
            <Dialog.Description className="drawer__desc">
              占位：源 Agent / Task 上下文 / Prompt 快照 / 上游演进树（后续实现）
            </Dialog.Description>
          </div>
          <div className="drawer__body" />
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
