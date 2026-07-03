import { Routes, Route, NavLink } from 'react-router'

function Home() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold mb-2">Hoshi</h1>
      <p className="text-muted-foreground">Real-sky astrological charting</p>
    </div>
  )
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b px-6 py-3 flex items-center gap-6">
        <span className="font-semibold tracking-tight">☽ Hoshi</span>
        <nav className="flex gap-4 text-sm">
          <NavLink to="/" end className={({ isActive }) => isActive ? 'text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'}>Charts</NavLink>
          <NavLink to="/compute" className={({ isActive }) => isActive ? 'text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'}>Compute</NavLink>
          <NavLink to="/info" className={({ isActive }) => isActive ? 'text-foreground font-medium' : 'text-muted-foreground hover:text-foreground'}>Info</NavLink>
        </nav>
      </header>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/compute" element={<div className="p-8 text-muted-foreground">Compute — coming soon</div>} />
          <Route path="/info" element={<div className="p-8 text-muted-foreground">Info — coming soon</div>} />
        </Routes>
      </main>
    </div>
  )
}
