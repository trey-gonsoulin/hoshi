import { describe, it, expect } from 'vitest'
import {
  lonToAngleDeg,
  polarPoint,
  sectorPath,
  staggerBodyRadii,
  getSignSectors,
  degreeTickLons,
} from './wheel'

describe('lonToAngleDeg', () => {
  it('places ASC lon at 180 degrees (9 oclock)', () => {
    expect(lonToAngleDeg(45, 45)).toBe(180)
    expect(lonToAngleDeg(0, 0)).toBe(180)
  })

  it('places lon 90 degrees ahead of ASC at the top', () => {
    expect(lonToAngleDeg(135, 45)).toBe(90)
  })

  it('places DSC (180 ahead of ASC) at 0 degrees (3 oclock)', () => {
    expect(lonToAngleDeg(225, 45)).toBe(0)
  })

  it('places IC (270 ahead of ASC) at -90 degrees (6 oclock)', () => {
    expect(lonToAngleDeg(315, 45)).toBe(-90)
  })

  it('handles lon slightly behind ASC (wrap-around)', () => {
    // lon=10, ascLon=350: lon is 20° ahead of ASC → svgAngle = 160°
    expect(lonToAngleDeg(10, 350)).toBe(160)
  })

  it('handles lon > 360', () => {
    expect(lonToAngleDeg(389, 0)).toBeCloseTo(lonToAngleDeg(29, 0), 5)
  })
})

describe('polarPoint', () => {
  it('returns the rightmost point at 0°', () => {
    const [x, y] = polarPoint(200, 200, 100, 0)
    expect(x).toBeCloseTo(300)
    expect(y).toBeCloseTo(200)
  })

  it('returns the topmost point at 270° (SVG y-down)', () => {
    const [x, y] = polarPoint(200, 200, 100, 270)
    expect(x).toBeCloseTo(200)
    expect(y).toBeCloseTo(100)
  })

  it('returns the leftmost point at 180°', () => {
    const [x, y] = polarPoint(200, 200, 100, 180)
    expect(x).toBeCloseTo(100)
    expect(y).toBeCloseTo(200)
  })
})

describe('sectorPath', () => {
  it('returns a non-empty string', () => {
    const d = sectorPath(200, 200, 185, 145, 0, 30, 0)
    expect(typeof d).toBe('string')
    expect(d.length).toBeGreaterThan(0)
  })

  it('starts with M and ends with Z', () => {
    const d = sectorPath(200, 200, 185, 145, 29, 53.41, 0)
    expect(d.startsWith('M')).toBe(true)
    expect(d.endsWith('Z')).toBe(true)
  })

  it('handles Pisces wrap-around (endLon > 360)', () => {
    const d = sectorPath(200, 200, 185, 145, 351.65, 389, 0)
    expect(d).not.toContain('NaN')
  })
})

describe('staggerBodyRadii', () => {
  it('returns baseR for isolated bodies', () => {
    const radii = staggerBodyRadii([0, 90, 180, 270], 100)
    expect(radii).toEqual([100, 100, 100, 100])
  })

  it('staggers conjunct bodies', () => {
    const radii = staggerBodyRadii([45, 47], 100)
    expect(radii[0]).not.toBe(radii[1])
  })

  it('returns empty array for empty input', () => {
    expect(staggerBodyRadii([], 100)).toEqual([])
  })
})

describe('getSignSectors', () => {
  it('returns 13 sectors for realsky mode', () => {
    const sectors = getSignSectors('realsky')
    expect(sectors).toHaveLength(13)
  })

  it('returns 12 sectors for tropical mode', () => {
    const sectors = getSignSectors('tropical')
    expect(sectors).toHaveLength(12)
  })

  it('returns 12 sectors for vedic mode', () => {
    const sectors = getSignSectors('vedic')
    expect(sectors).toHaveLength(12)
  })

  it('realsky sectors span the full circle (29° to 389°)', () => {
    const sectors = getSignSectors('realsky')
    const sorted = [...sectors].sort((a, b) => a.startLon - b.startLon)
    expect(sorted[0].startLon).toBeCloseTo(29)
    const last = sorted[sorted.length - 1]
    expect(last.endLon).toBeCloseTo(389)
  })

  it('tropical sectors start at 0° and each span 30°', () => {
    const sectors = getSignSectors('tropical')
    expect(sectors[0].startLon).toBe(0)
    sectors.forEach((s) => {
      expect(s.endLon - s.startLon).toBeCloseTo(30)
    })
  })

  it('every sector has a non-empty glyph and abbrev', () => {
    for (const mode of ['realsky', 'tropical']) {
      const sectors = getSignSectors(mode)
      sectors.forEach((s) => {
        expect(s.glyph.length).toBeGreaterThan(0)
        expect(s.abbrev.length).toBeGreaterThan(0)
      })
    }
  })
})

describe('degreeTickLons', () => {
  it('returns 36 ticks for step=10', () => {
    expect(degreeTickLons(10)).toHaveLength(36)
  })

  it('starts at 0 and ends at 350 for step=10', () => {
    const ticks = degreeTickLons(10)
    expect(ticks[0]).toBe(0)
    expect(ticks[ticks.length - 1]).toBe(350)
  })

  it('returns 72 ticks for step=5', () => {
    expect(degreeTickLons(5)).toHaveLength(72)
  })
})
