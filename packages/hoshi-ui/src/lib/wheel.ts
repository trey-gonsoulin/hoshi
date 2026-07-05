import { getAllSigns } from './astroInfo'

export interface SignSector {
  name: string
  abbrev: string
  startLon: number
  endLon: number
  element: string
  glyph: string
}

export const SIGN_GLYPHS: Record<string, string> = {
  Aries: '♈',
  Taurus: '♉',
  Gemini: '♊',
  Cancer: '♋',
  Leo: '♌',
  Virgo: '♍',
  Libra: '♎',
  Scorpio: '♏',
  Ophiuchus: '⛎',
  Sagittarius: '♐',
  Capricorn: '♑',
  Aquarius: '♒',
  Pisces: '♓',
}

export const SIGN_ABBREVS: Record<string, string> = {
  Aries: 'Ari',
  Taurus: 'Tau',
  Gemini: 'Gem',
  Cancer: 'Cnc',
  Leo: 'Leo',
  Virgo: 'Vir',
  Libra: 'Lib',
  Scorpio: 'Sco',
  Ophiuchus: 'Oph',
  Sagittarius: 'Sgr',
  Capricorn: 'Cap',
  Aquarius: 'Aqr',
  Pisces: 'Psc',
}

// Muted element fills that read in both light and dark themes.
// Air is teal (~185° hue) and Water is indigo-violet (~245°) so they stay
// distinguishable at low opacity — especially in dark mode.
export const ELEMENT_FILL: Record<string, string> = {
  Fire: 'rgba(211, 68, 38, 0.21)',
  Earth: 'rgba(45, 115, 70, 0.18)',
  Air: 'rgba(18, 148, 165, 0.24)',
  Water: 'rgba(75, 45, 162, 0.24)',
}

/** Ecliptic longitudes for degree tick marks around the outer ring. */
export function degreeTickLons(step = 10): number[] {
  return Array.from({ length: Math.floor(360 / step) }, (_, i) => i * step)
}

const TROP_NAMES = [
  'Aries',
  'Taurus',
  'Gemini',
  'Cancer',
  'Leo',
  'Virgo',
  'Libra',
  'Scorpio',
  'Sagittarius',
  'Capricorn',
  'Aquarius',
  'Pisces',
]

/** Sign sectors for the given zodiac mode.
 * For realsky: 13 IAU sectors from astroData (J2000-fixed boundaries).
 * For tropical/vedic: 12 equal 30° sectors from 0°.
 * Note: body `lon` values are equinox-of-date; IAU boundaries are J2000.
 * The ~0.36° precession offset (as of 2026) is sub-pixel and acceptable for v1. */
export function getSignSectors(mode: string): SignSector[] {
  const signs = getAllSigns()
  if (mode === 'realsky') {
    return Object.values(signs)
      .filter((s) => s.lo != null)
      .sort((a, b) => a.lo - b.lo)
      .map((s) => ({
        name: s.name,
        abbrev: SIGN_ABBREVS[s.name] ?? s.name.slice(0, 3),
        startLon: s.lo,
        endLon: s.lo + s.size,
        element: s.element,
        glyph: SIGN_GLYPHS[s.name] ?? s.name[0],
      }))
  }
  return TROP_NAMES.map((name, i) => ({
    name,
    abbrev: SIGN_ABBREVS[name] ?? name.slice(0, 3),
    startLon: i * 30,
    endLon: (i + 1) * 30,
    element: signs[name]?.element ?? 'Fire',
    glyph: SIGN_GLYPHS[name] ?? name[0],
  }))
}

/** Convert ecliptic longitude to SVG angle (degrees).
 * ascLon: ASC longitude; defaults to 0 so the vernal equinox sits at 9 o'clock.
 * SVG: 0° = right, increases clockwise.
 * Zodiac: increasing longitude goes counterclockwise on the wheel. */
export function lonToAngleDeg(lon: number, ascLon = 0): number {
  return 180 - ((lon - ascLon + 720) % 360)
}

export function toRad(deg: number): number {
  return (deg * Math.PI) / 180
}

/** Cartesian point on a circle at the given SVG angle. */
export function polarPoint(
  cx: number,
  cy: number,
  r: number,
  angleDeg: number,
): [number, number] {
  const rad = toRad(angleDeg)
  return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
}

function fmt(n: number): string {
  return n.toFixed(3)
}

/** SVG path string for a donut sector spanning startLon→endLon (ecliptic degrees). */
export function sectorPath(
  cx: number,
  cy: number,
  rOuter: number,
  rInner: number,
  startLon: number,
  endLon: number,
  ascLon: number,
): string {
  const a1 = lonToAngleDeg(startLon, ascLon)
  const a2 = lonToAngleDeg(endLon, ascLon)
  const [ox1, oy1] = polarPoint(cx, cy, rOuter, a1)
  const [ox2, oy2] = polarPoint(cx, cy, rOuter, a2)
  const [ix1, iy1] = polarPoint(cx, cy, rInner, a1)
  const [ix2, iy2] = polarPoint(cx, cy, rInner, a2)
  const span = (endLon - startLon + 360) % 360
  const large = span > 180 ? 1 : 0
  // Outer arc: counterclockwise in SVG (sweep=0); inner arc: clockwise (sweep=1)
  return (
    `M ${fmt(ox1)} ${fmt(oy1)} ` +
    `A ${rOuter} ${rOuter} 0 ${large} 0 ${fmt(ox2)} ${fmt(oy2)} ` +
    `L ${fmt(ix2)} ${fmt(iy2)} ` +
    `A ${rInner} ${rInner} 0 ${large} 1 ${fmt(ix1)} ${fmt(iy1)} Z`
  )
}

/** Compute per-body display radii, staggering bodies within `gapDeg` of each other
 * to reduce glyph overlap near conjunctions. */
export function staggerBodyRadii(
  lons: number[],
  baseR: number,
  gapDeg = 7,
  step = 13,
): number[] {
  const n = lons.length
  if (n === 0) return []

  const order = Array.from({ length: n }, (_, i) => i).sort(
    (a, b) => lons[a] - lons[b],
  )

  const radii = new Array<number>(n).fill(baseR)
  let clusterPos = 0

  for (let j = 1; j < n; j++) {
    const prev = order[j - 1]
    const curr = order[j]
    const diff = (lons[curr] - lons[prev] + 360) % 360
    if (diff < gapDeg) {
      clusterPos = (clusterPos % 3) + 1
      const offset = clusterPos === 1 ? step : clusterPos === 2 ? -step : 0
      radii[curr] = baseR + offset
    } else {
      clusterPos = 0
    }
  }

  return radii
}
