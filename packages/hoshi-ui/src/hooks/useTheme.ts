import { useState, useEffect } from 'react'

type Theme = 'light' | 'dark'

function resolveInitial(): Theme {
  const stored = localStorage.getItem('hoshi:theme')
  if (stored === 'dark' || stored === 'light') return stored
  return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(resolveInitial)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('hoshi:theme', theme)
  }, [theme])

  const toggle = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  return { theme, toggle }
}
