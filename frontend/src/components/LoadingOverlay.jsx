const STATUS_MESSAGES = {
  pending: { main: '작업을 대기 중입니다', sub: '큐에서 처리를 기다리고 있어요...' },
  processing: { main: '광고를 제작하는 중입니다', sub: 'AI가 이미지를 생성하고 있어요 (약 1~2분)' },
}

export default function LoadingOverlay({ status }) {
  const msg = STATUS_MESSAGES[status] || STATUS_MESSAGES.pending

  return (
    <div
      className="fixed inset-0 bg-black/30 z-50 flex items-center justify-center"
      style={{ backdropFilter: 'blur(4px)' }}
    >
      <div className="bg-white p-12 flex flex-col items-center gap-6 shadow-2xl">
        <div className="spinner" style={{ width: '48px', height: '48px' }} />
        <p className="font-bold text-on-surface text-lg">{msg.main}</p>
        <p className="text-sm text-on-surface-variant">{msg.sub}</p>
      </div>
    </div>
  )
}
