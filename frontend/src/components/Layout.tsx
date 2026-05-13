import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth.store'

// `end: true` activa el NavLink solo en match exacto (no para sub-rutas).
// Crucial para `/evaluaciones`: sin `end`, también se ilumina cuando estás en
// `/evaluaciones/iniciar` o `/evaluaciones/:id` → highlight duplicado.
//
// "Registro manual" (/evaluaciones/nueva) era el flujo legacy donde se
// insertaba un dictamen manualmente en BD para pruebas. Hoy obsoleto: la
// captura completa la dispara "Iniciar Evaluación" vía subprocess. La ruta
// se conserva por compatibilidad con código antiguo, pero no se expone.
const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊', permiso: null, end: true },
  { to: '/calibracion', label: 'Calibración', icon: '🎯', permiso: 'baseline_somnolencia:registrar', end: true },
  { to: '/evaluaciones/iniciar', label: 'Iniciar Evaluación', icon: '▶️', permiso: 'evaluacion:registrar', end: true },
  { to: '/evaluaciones', label: 'Mis Evaluaciones', icon: '📋', permiso: 'evaluacion:ver_propias', end: true },
  { to: '/usuarios', label: 'Usuarios', icon: '👥', permiso: 'usuario:gestionar', end: true },
]

export default function Layout() {
  const { user, logout, hasPermission } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)

  // Cerrar el drawer al navegar (móvil)
  useEffect(() => {
    setDrawerOpen(false)
  }, [location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const visibleItems = navItems.filter(
    (item) => item.permiso === null || hasPermission(item.permiso)
  )

  const sidebarContent = (
    <>
      <div className="px-6 py-5 border-b border-slate-700 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-white">VigilanceAI</h1>
          <p className="text-xs text-slate-400 mt-0.5">Sistema de detección de fatiga</p>
        </div>
        <button
          onClick={() => setDrawerOpen(false)}
          className="lg:hidden text-slate-400 hover:text-white p-1"
          aria-label="Cerrar menú"
        >
          ✕
        </button>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {visibleItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`
            }
          >
            <span className="text-base">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-slate-700">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-sm font-bold flex-shrink-0">
            {user?.nombre?.[0]}{user?.apellido?.[0]}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-white truncate">
              {user?.nombre} {user?.apellido}
            </p>
            <p className="text-xs text-slate-400 capitalize truncate">{user?.rol}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full text-left px-3 py-2 text-xs text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-colors"
        >
          Cerrar sesión
        </button>
      </div>
    </>
  )

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar — fijo en lg+, drawer en móvil */}
      <aside className="hidden lg:flex w-64 bg-slate-900 text-white flex-col shadow-xl flex-shrink-0">
        {sidebarContent}
      </aside>

      {/* Drawer móvil */}
      {drawerOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setDrawerOpen(false)}
          aria-hidden="true"
        />
      )}
      <aside
        className={`lg:hidden fixed inset-y-0 left-0 w-64 max-w-[80%] bg-slate-900 text-white flex flex-col shadow-xl z-50 transform transition-transform duration-200 ${
          drawerOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        {/* Topbar móvil — solo visible bajo lg */}
        <header className="lg:hidden sticky top-0 z-30 bg-white border-b border-slate-200 flex items-center gap-3 px-4 h-14 shadow-sm">
          <button
            onClick={() => setDrawerOpen(true)}
            className="p-2 -ml-2 text-slate-700 hover:bg-slate-100 rounded-lg"
            aria-label="Abrir menú"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
          <span className="font-semibold text-slate-900">VigilanceAI</span>
        </header>

        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
