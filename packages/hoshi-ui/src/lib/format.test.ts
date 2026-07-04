import { describe, it, expect } from 'vitest'
import { formatDeg, formatLon } from './format'

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
