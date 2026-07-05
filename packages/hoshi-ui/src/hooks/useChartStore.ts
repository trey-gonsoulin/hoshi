import { useState, useCallback, useContext, createContext } from 'react'
import type { ChartCompute } from '@/api/client'

export interface PlacementSummary {
  sun?: string
  moon?: string
  asc?: string
}

export interface SavedChart {
  id: string
  name: string
  savedAt: string
  input: ChartCompute
  placements?: PlacementSummary
  tags?: string[]
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
  save: (name: string, input: ChartCompute, placements?: PlacementSummary) => SavedChart
  update: (id: string, patch: { name?: string; input?: ChartCompute; placements?: PlacementSummary; tags?: string[] }) => void
  remove: (id: string) => void
  reorder: (fromIdx: number, toIdx: number) => void
  get: (id: string) => SavedChart | undefined
}

export const ChartStoreContext = createContext<ChartStore | null>(null)

export function useChartStoreProvider(): ChartStore {
  const [charts, setCharts] = useState<SavedChart[]>(loadFromStorage)

  const save = useCallback((name: string, input: ChartCompute, placements?: PlacementSummary): SavedChart => {
    const entry: SavedChart = {
      id: crypto.randomUUID(),
      name: name.trim(),
      savedAt: new Date().toISOString(),
      input,
      placements,
    }
    setCharts((prev) => {
      const next = [entry, ...prev]
      persistToStorage(next)
      return next
    })
    return entry
  }, [])

  const update = useCallback((id: string, patch: { name?: string; input?: ChartCompute; placements?: PlacementSummary; tags?: string[] }) => {
    setCharts((prev) => {
      const next = prev.map((c) =>
        c.id === id ? { ...c, ...patch } : c,
      )
      persistToStorage(next)
      return next
    })
  }, [])

  const remove = useCallback((id: string) => {
    setCharts((prev) => {
      const next = prev.filter((c) => c.id !== id)
      persistToStorage(next)
      return next
    })
  }, [])

  const reorder = useCallback((fromIdx: number, toIdx: number) => {
    if (fromIdx === toIdx) return
    setCharts((prev) => {
      const next = [...prev]
      const [item] = next.splice(fromIdx, 1)
      next.splice(toIdx, 0, item)
      persistToStorage(next)
      return next
    })
  }, [])

  const get = useCallback(
    (id: string) => charts.find((c) => c.id === id),
    [charts],
  )

  return { charts, save, update, remove, reorder, get }
}

export function useChartStore(): ChartStore {
  const ctx = useContext(ChartStoreContext)
  if (!ctx) throw new Error('useChartStore must be used within ChartStoreContext.Provider')
  return ctx
}
