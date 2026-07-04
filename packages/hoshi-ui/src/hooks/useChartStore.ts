import { useState, useCallback, useContext, createContext } from 'react'
import type { ChartCompute } from '@/api/client'

export interface SavedChart {
  id: string
  name: string
  savedAt: string
  input: ChartCompute
}

const STORAGE_KEY = 'hoshi:charts'

function loadFromStorage(): SavedChart[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]')
  } catch {
    return []
  }
}

function persistToStorage(charts: SavedChart[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(charts))
}

interface ChartStore {
  charts: SavedChart[]
  save: (name: string, input: ChartCompute) => SavedChart
  remove: (id: string) => void
  get: (id: string) => SavedChart | undefined
}

export const ChartStoreContext = createContext<ChartStore | null>(null)

export function useChartStoreProvider(): ChartStore {
  const [charts, setCharts] = useState<SavedChart[]>(loadFromStorage)

  const save = useCallback((name: string, input: ChartCompute): SavedChart => {
    const entry: SavedChart = {
      id: crypto.randomUUID(),
      name: name.trim(),
      savedAt: new Date().toISOString(),
      input,
    }
    setCharts((prev) => {
      const next = [entry, ...prev]
      persistToStorage(next)
      return next
    })
    return entry
  }, [])

  const remove = useCallback((id: string) => {
    setCharts((prev) => {
      const next = prev.filter((c) => c.id !== id)
      persistToStorage(next)
      return next
    })
  }, [])

  const get = useCallback(
    (id: string) => charts.find((c) => c.id === id),
    [charts],
  )

  return { charts, save, remove, get }
}

export function useChartStore(): ChartStore {
  const ctx = useContext(ChartStoreContext)
  if (!ctx) throw new Error('useChartStore must be used within ChartStoreContext.Provider')
  return ctx
}
