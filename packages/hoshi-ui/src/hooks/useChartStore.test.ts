import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useChartStoreProvider } from './useChartStore'

const INPUT = {
  date: '1981-09-04',
  time: '21:47',
  tz: 'America/Chicago',
  lat: 29.76,
  lon: -95.37,
  mode: 'realsky' as const,
  houses: 'porphyry' as const,
  details: true,
  aspects: true,
  cusps: true,
}

beforeEach(() => {
  localStorage.clear()
})

describe('save', () => {
  it('returns a chart with a non-empty id', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let saved: ReturnType<typeof result.current.save>

    act(() => { saved = result.current.save('Beyoncé', INPUT) })

    expect(saved!.id).toBeTruthy()
    expect(typeof saved!.id).toBe('string')
    expect(saved!.id.length).toBeGreaterThan(0)
  })

  it('adds a chart and returns it', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let saved: ReturnType<typeof result.current.save>

    act(() => {
      saved = result.current.save('Beyoncé', INPUT)
    })

    expect(result.current.charts).toHaveLength(1)
    expect(result.current.charts[0].name).toBe('Beyoncé')
    expect(saved!.id).toBeTruthy()
  })

  it('prepends new charts', () => {
    const { result } = renderHook(() => useChartStoreProvider())

    act(() => { result.current.save('First', INPUT) })
    act(() => { result.current.save('Second', INPUT) })

    expect(result.current.charts[0].name).toBe('Second')
    expect(result.current.charts[1].name).toBe('First')
  })

  it('stores placements when provided', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    const placements = { sun: '♍', moon: '♊', asc: '♊' }

    act(() => { result.current.save('Test', INPUT, placements) })

    expect(result.current.charts[0].placements).toEqual(placements)
  })

  it('persists to localStorage', () => {
    const { result } = renderHook(() => useChartStoreProvider())

    act(() => { result.current.save('Persisted', INPUT) })

    const stored = JSON.parse(localStorage.getItem('hoshi:charts') ?? '[]')
    expect(stored).toHaveLength(1)
    expect(stored[0].name).toBe('Persisted')
  })
})

describe('remove', () => {
  it('removes a chart by id', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let id: string

    act(() => {
      const chart = result.current.save('To delete', INPUT)
      id = chart.id
    })
    act(() => { result.current.remove(id) })

    expect(result.current.charts).toHaveLength(0)
  })

  it('leaves other charts intact', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let keepId = ''

    act(() => {
      const a = result.current.save('Keep', INPUT)
      keepId = a.id
      result.current.save('Delete', INPUT)
    })
    act(() => {
      const deleteId = result.current.charts[0].id
      result.current.remove(deleteId)
    })

    expect(result.current.charts).toHaveLength(1)
    expect(result.current.charts[0].id).toBe(keepId)
  })
})

describe('reorder', () => {
  it('moves an item from one index to another', () => {
    const { result } = renderHook(() => useChartStoreProvider())

    act(() => {
      result.current.save('A', INPUT)
      result.current.save('B', INPUT)
      result.current.save('C', INPUT)
    })
    // After prepend order is: C, B, A
    act(() => { result.current.reorder(0, 2) })

    expect(result.current.charts.map((c) => c.name)).toEqual(['B', 'A', 'C'])
  })

  it('is a no-op when from === to', () => {
    const { result } = renderHook(() => useChartStoreProvider())

    act(() => {
      result.current.save('A', INPUT)
      result.current.save('B', INPUT)
    })
    const before = result.current.charts.map((c) => c.id)
    act(() => { result.current.reorder(0, 0) })

    expect(result.current.charts.map((c) => c.id)).toEqual(before)
  })
})

describe('update', () => {
  it('updates name', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let id: string

    act(() => { id = result.current.save('Old name', INPUT).id })
    act(() => { result.current.update(id, { name: 'New name' }) })

    expect(result.current.charts[0].name).toBe('New name')
  })

  it('clears placements when set to undefined', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let id: string

    act(() => {
      id = result.current.save('Chart', INPUT, { sun: '♌' }).id
    })
    act(() => { result.current.update(id, { placements: undefined }) })

    expect(result.current.charts[0].placements).toBeUndefined()
  })
})

describe('get', () => {
  it('returns a defined chart for a valid id from save', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let saved: ReturnType<typeof result.current.save>

    act(() => { saved = result.current.save('Find me', INPUT) })

    const found = result.current.get(saved!.id)
    expect(found).toBeDefined()
    expect(found!.name).toBe('Find me')
    expect(found!.id).toBe(saved!.id)
  })

  it('retrieves a chart by id', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    let id = ''

    act(() => { id = result.current.save('Find me', INPUT).id })

    expect(result.current.get(id)?.name).toBe('Find me')
  })

  it('returns undefined for an unknown id', () => {
    const { result } = renderHook(() => useChartStoreProvider())
    expect(result.current.get('no-such-id')).toBeUndefined()
  })
})
