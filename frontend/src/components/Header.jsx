export default function Header() {
  return (
    <header className="flex justify-between items-center px-8 fixed top-0 left-64 right-0 h-16 bg-white border-b border-slate-200/50 shadow-sm z-10">
      <span className="text-xl font-black text-slate-900">AI 광고 스튜디오</span>
      <div className="h-8 w-8 bg-surface-container rounded-full flex items-center justify-center">
        <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: '20px' }}>person</span>
      </div>
    </header>
  )
}
