import { Routes, Route, NavLink } from 'react-router'
import { Sun, Moon } from 'lucide-react'
import { SkyPage } from '@/pages/SkyPage'
import { ComputePage } from '@/pages/ComputePage'
import { ChartsPage } from '@/pages/ChartsPage'
import { ChartDetailPage } from '@/pages/ChartDetailPage'
import { TransitsPage } from '@/pages/TransitsPage'
import { ForecastPage } from '@/pages/ForecastPage'
import { ComparePage } from '@/pages/ComparePage'
import { CompositePage } from '@/pages/CompositePage'
import { CompositeTransitsPage } from '@/pages/CompositeTransitsPage'
import { BirthRangePage } from '@/pages/BirthRangePage'
import { InfoPage } from '@/pages/InfoPage'
import { InfoCategoryPage } from '@/pages/InfoCategoryPage'
import { InfoDetailPage } from '@/pages/InfoDetailPage'
import { useTheme } from '@/hooks/useTheme'

function navClass({ isActive }: { isActive: boolean }) {
  return isActive
    ? 'text-foreground font-medium'
    : 'text-muted-foreground hover:text-foreground transition-colors'
}

export default function App() {
  const { theme, toggle } = useTheme()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b px-6 py-3 flex items-center gap-6">
        <span className="font-semibold tracking-tight text-sm">✦ hoshi</span>
        <nav className="flex gap-5 text-sm">
          <NavLink to="/" end className={navClass}>Sky</NavLink>
          <NavLink to="/charts" className={navClass}>Charts</NavLink>
          <NavLink to="/compute" className={navClass}>Compute</NavLink>
          <NavLink to="/birthrange" className={navClass}>Birth Range</NavLink>
          <NavLink to="/info" className={navClass}>Info</NavLink>
        </nav>
        <button
          onClick={toggle}
          aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          className="ml-auto text-muted-foreground hover:text-foreground transition-colors"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </header>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<SkyPage />} />
          <Route path="/charts" element={<ChartsPage />} />
          <Route path="/compute" element={<ComputePage />} />
          <Route path="/charts/:id" element={<ChartDetailPage />} />
          <Route path="/charts/:id/transits" element={<TransitsPage />} />
          <Route path="/charts/:id/forecast" element={<ForecastPage />} />
          <Route path="/charts/:id/compare" element={<ComparePage />} />
          <Route path="/charts/:id/composite" element={<CompositePage />} />
          <Route path="/charts/:id/composite-transits" element={<CompositeTransitsPage />} />
          <Route path="/birthrange" element={<BirthRangePage />} />
          <Route path="/info" element={<InfoPage />} />
          <Route path="/info/:category" element={<InfoCategoryPage />} />
          <Route path="/info/:category/:name" element={<InfoDetailPage />} />
        </Routes>
      </main>
    </div>
  )
}
