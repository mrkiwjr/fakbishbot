import { NavLink } from 'react-router-dom'
import { DollarSign, Gamepad2, Flame, Home } from 'lucide-react'

const tabs = [
  { to: '/', icon: Home, label: 'Главная' },
  { to: '/tariffs', icon: DollarSign, label: 'Тарифы' },
  { to: '/booking', icon: Gamepad2, label: 'Бронь' },
  { to: '/promos', icon: Flame, label: 'Акции' },
]

export default function NavBar() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-k-black/95 backdrop-blur-md border-t border-k-border/50">
      <div className="flex justify-around items-center h-[60px] max-w-lg mx-auto px-2">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              className={({ isActive }) =>
                `relative flex flex-col items-center gap-1 px-4 py-1.5 transition-all ${
                  isActive ? 'text-k-white' : 'text-k-dim'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <div
                      className="absolute -top-1 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full pointer-events-none"
                      style={{ background: 'radial-gradient(circle, rgba(196,30,30,0.35) 0%, transparent 70%)' }}
                    />
                  )}
                  <Icon size={22} strokeWidth={isActive ? 2.2 : 1.5} className={isActive ? 'text-k-white' : ''} />
                  <span className={`text-[10px] font-medium tracking-wide ${isActive ? 'text-k-white' : ''}`}>
                    {tab.label}
                  </span>
                </>
              )}
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
