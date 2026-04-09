const NAV_ITEMS = [
  { icon: 'dashboard',      label: 'Dashboard',     active: false },
  { icon: 'auto_awesome',   label: 'Ad Creator',    active: true  },
  { icon: 'folder_special', label: 'Asset Library', active: false },
  { icon: 'settings',       label: 'Settings',      active: false },
]

export default function Sidebar({ onReset }) {
  return (
    <aside className="flex flex-col h-screen fixed left-0 top-0 w-64 border-r border-slate-200/50 bg-slate-50 z-20">
      <div className="p-6">
        <h1 className="text-2xl font-semibold tracking-tighter text-slate-900">AdAI Studio</h1>
        <p className="font-medium tracking-tight text-xs uppercase text-slate-500 mt-1">소상공인 광고 서비스</p>
      </div>

      <nav className="flex-1 px-4 space-y-1">
        {NAV_ITEMS.map(({ icon, label, active }) => (
          <a
            key={label}
            className={
              active
                ? 'flex items-center px-4 py-3 space-x-3 text-blue-600 font-bold border-r-4 border-blue-600 tracking-tight text-sm uppercase'
                : 'flex items-center px-4 py-3 space-x-3 text-slate-500 font-medium tracking-tight text-sm uppercase hover:bg-slate-100 transition-colors cursor-pointer'
            }
          >
            <span className="material-symbols-outlined">{icon}</span>
            <span>{label}</span>
          </a>
        ))}
      </nav>

      <div className="px-4 py-6 border-t border-slate-200/50">
        <button
          onClick={onReset}
          className="w-full py-3 bg-primary text-on-primary font-bold tracking-tight text-sm uppercase active:scale-95 transition-transform hover:bg-primary-dim"
        >
          대화 초기화
        </button>
      </div>
    </aside>
  )
}
