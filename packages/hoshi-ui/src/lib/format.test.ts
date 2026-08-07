import { describe, it, expect } from 'vitest'
import { formatDeg, formatLon, chartToText } from './format'
import type { ChartOutput } from '@/api/client'

describe('formatDeg', () => {
  it('formats whole degrees', () => {
    expect(formatDeg(24)).toBe("24°00'")
  })

  it('formats degrees with minutes', () => {
    expect(formatDeg(24.5)).toBe("24°30'")
  })

  it('pads single-digit minutes', () => {
    expect(formatDeg(3.1)).toBe("3°06'")
  })

  it('rounds fractional minutes', () => {
    expect(formatDeg(0.999)).toBe("0°60'")
  })

  it('handles zero', () => {
    expect(formatDeg(0)).toBe("0°00'")
  })
})

describe('formatLon', () => {
  it('formats to two decimal places', () => {
    expect(formatLon(54.2134)).toBe('54.21°')
  })

  it('formats zero', () => {
    expect(formatLon(0)).toBe('0.00°')
  })

  it('formats whole number with trailing zeros', () => {
    expect(formatLon(180)).toBe('180.00°')
  })
})

const minimalChart: ChartOutput = {
  chart: { name: 'Test', when: '2000-01-01 12:00 UTC', mode: 'realsky' },
  warnings: [],
  bodies: [
    { kind: 'planet', name: 'Sun', sign: 'Sagittarius', signSymbol: '♐', degree: 10.5, lon: 250.5, rx: false, approximate: false, dignity: 'neutral', symbol: '☉' },
    { kind: 'planet', name: 'Moon', sign: 'Taurus', signSymbol: '♉', degree: 22.0, lon: 52.0, rx: false, approximate: false, dignity: '', symbol: '☽' },
  ],
  cusps: [],
}

describe('chartToText', () => {
  it('includes chart name and date', () => {
    const text = chartToText(minimalChart)
    expect(text).toContain('# Test')
    expect(text).toContain('2000-01-01 12:00 UTC')
  })

  it('includes body placements', () => {
    const text = chartToText(minimalChart)
    expect(text).toContain("Sun: Sagittarius 10°30'")
    expect(text).toContain("Moon: Taurus 22°00'")
  })

  it('omits house when null', () => {
    const text = chartToText(minimalChart)
    expect(text).not.toContain('House')
  })

  it('includes house when present', () => {
    const withHouse: ChartOutput = {
      ...minimalChart,
      bodies: [{ ...minimalChart.bodies[0], house: 3 }, minimalChart.bodies[1]],
    }
    expect(chartToText(withHouse)).toContain('House 3')
  })

  it('marks retrograde bodies', () => {
    const withRx: ChartOutput = {
      ...minimalChart,
      bodies: [{ ...minimalChart.bodies[0], rx: true }, minimalChart.bodies[1]],
    }
    expect(chartToText(withRx)).toContain('(Rx)')
  })

  it('includes aspects when present', () => {
    const withAspects: ChartOutput = {
      ...minimalChart,
      aspects: [{ bodyA: 'Sun', signA: 'Sag', bodyB: 'Moon', signB: 'Tau', name: 'trine', symbol: '△', angle: 120, orb: 1.5, kind: 'Major' }],
    }
    const text = chartToText(withAspects)
    expect(text).toContain('## Aspects')
    expect(text).toContain('Sun trine Moon (orb 1.5°)')
  })

  it('includes cusps when present', () => {
    const withCusps: ChartOutput = { ...minimalChart, cusps: [10.5, 40.0] }
    const text = chartToText(withCusps)
    expect(text).toContain('## House cusps')
    expect(text).toContain('House 1: 10.50°')
  })

  it('omits location when unknown', () => {
    expect(chartToText(minimalChart)).not.toContain('Location:')
  })

  it('includes location when known', () => {
    const withLoc: ChartOutput = {
      ...minimalChart,
      chart: { ...minimalChart.chart, lat: 40.7128, lon: -74.006 },
    }
    expect(chartToText(withLoc)).toContain('Location: 40.7128, -74.0060')
  })
})
