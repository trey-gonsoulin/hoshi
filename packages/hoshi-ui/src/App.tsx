import { Routes, Route, NavLink } from 'react-router'
import { ComputePage } from '@/pages/ComputePage'
import { ChartsPage } from '@/pages/ChartsPage'
import { ChartDetailPage } from '@/pages/ChartDetailPage'
import { TransitsPage } from '@/pages/TransitsPage'
import { ComparePage } from '@/pages/ComparePage'

function navClass({ isActive }: { isActive: boolean }) {
  return isActive
    ? 'text-foreground font-medium'
    : 'text-muted-foreground hover:text-foreground transition-colors'
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b px-6 py-3 flex items-center gap-6">
        <span className="font-semibold tracking-tight text-sm">☽ hoshi</span>
        <nav className="flex gap-5 text-sm">
          <NavLink to="/" end className={navClass}>Charts</NavLink>
          <NavLink to="/compute" className={navClass}>Compute</NavLink>
          <NavLink to="/info" className={navClass}>Info</NavLink>
        </nav>
      </header>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<ChartsPage />} />
          <Route path="/compute" element={<ComputePage />} />
          <Route path="/charts/:id" element={<ChartDetailPage />} />
          <Route path="/charts/:id/transits" element={<TransitsPage />} />
          <Route path="/charts/:id/compare" element={<ComparePage />} />
          <Route path="/info" element={<div className="max-w-2xl mx-auto px-6 py-10 text-muted-foreground text-sm">Info browser — coming in Phase 6.</div>} />
        </Routes>
      </main>
    </div>
  )
}
