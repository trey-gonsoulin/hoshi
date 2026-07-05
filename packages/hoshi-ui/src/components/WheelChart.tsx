import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import {
  lonToAngleDeg,
  polarPoint,
  sectorPath,
  getSignSectors,
  staggerBodyRadii,
  degreeTickLons,
  ELEMENT_FILL,
} from '@/lib/wheel'
import type { BodyEntry } from '@/api/client'

// Viewbox dimensions
const SIZE = 440
const CX = 220
const CY = 220

// Radii, outer → inner
const R_OUTER = 212         // outer ring border
const R_TICK_IN = 207       // inner end of degree ticks (4px visible height)
const R_SIGN_OUTER = 205    // outer edge of sign ring
const R_SIGN_INNER = 159    // inner edge of sign ring (46px band)
const R_GLYPH = 191         // sign glyph — upper portion of ring
const R_ABBREV = 172        // sign abbreviation — lower portion
const R_PTICK_OUT = 159     // planet position tick start (sign ring inner edge)
const R_PTICK_IN = 151      // planet position tick end (8px)
const R_BODY = 114          // planet glyph base radius
const R_HOUSE_NUM = 70      // house number labels
const R_CENTER = 38         // inner circle border

const TICKS = degreeTickLons(10)

interface WheelChartProps {
  bodies: BodyEntry[]
  /** House cusp longitudes. When empty, 0° ecliptic sits at 9 o'clock. */
  cusps: number[]
  mode: string
}

export function WheelChart({ bodies, cusps, mode }: WheelChartProps) {
  const ascLon = cusps.length > 0 ? cusps[0] : 0
  const sectors = useMemo(() => getSignSectors(mode), [mode])
  const bodyRadii = useMemo(
    () => staggerBodyRadii(bodies.map((b) => b.lon), R_BODY),
    [bodies],
  )

  return (
    <svg
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      className="w-full max-w-[500px] mx-auto block"
      aria-label="Astrology wheel chart"
    >
      {/* ── Sign ring ───────────────────────────────────────────────────── */}
      {sectors.map((sector) => {
        const fill = ELEMENT_FILL[sector.element] ?? 'rgba(128,128,128,0.1)'
        const d = sectorPath(CX, CY, R_SIGN_OUTER, R_SIGN_INNER, sector.startLon, sector.endLon, ascLon)
        const span = sector.endLon - sector.startLon
        const midLon = sector.startLon + span / 2
        const midAngle = lonToAngleDeg(midLon, ascLon)
        const showAbbrev = span >= 22
        const glyphR = showAbbrev ? R_GLYPH : (R_SIGN_INNER + R_SIGN_OUTER) / 2
        const [glyphX, glyphY] = polarPoint(CX, CY, glyphR, midAngle)
        const [abbrevX, abbrevY] = polarPoint(CX, CY, R_ABBREV, midAngle)

        return (
          <g key={sector.name}>
            <path
              d={d}
              fill={fill}
              stroke="currentColor"
              strokeOpacity={0.1}
              strokeWidth={0.5}
            />
            {span >= 6 && (
              <text
                x={glyphX}
                y={glyphY}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={span >= 18 ? 13 : 10}
                fill="currentColor"
                fillOpacity={0.55}
                className="select-none"
              >
                {sector.glyph}
              </text>
            )}
            {showAbbrev && (
              <text
                x={abbrevX}
                y={abbrevY}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={7.5}
                fill="currentColor"
                fillOpacity={0.38}
                className="select-none"
                letterSpacing={0.3}
              >
                {sector.abbrev}
              </text>
            )}
          </g>
        )
      })}

      {/* ── Ring borders ────────────────────────────────────────────────── */}
      <circle
        cx={CX} cy={CY} r={R_OUTER}
        fill="none" stroke="currentColor" strokeOpacity={0.2} strokeWidth={0.75}
      />
      <circle
        cx={CX} cy={CY} r={R_SIGN_OUTER}
        fill="none" stroke="currentColor" strokeOpacity={0.1} strokeWidth={0.4}
      />
      <circle
        cx={CX} cy={CY} r={R_SIGN_INNER}
        fill="none" stroke="currentColor" strokeOpacity={0.14} strokeWidth={0.5}
      />

      {/* ── Degree tick ring — signature precision element ───────────────── */}
      {TICKS.map((lon) => {
        const angle = lonToAngleDeg(lon, ascLon)
        const [x1, y1] = polarPoint(CX, CY, R_OUTER, angle)
        const [x2, y2] = polarPoint(CX, CY, R_TICK_IN, angle)
        return (
          <line
            key={lon}
            x1={x1} y1={y1} x2={x2} y2={y2}
            stroke="currentColor"
            strokeOpacity={0.16}
            strokeWidth={0.75}
          />
        )
      })}

      {/* ── House cusp lines ─────────────────────────────────────────────── */}
      {cusps.length > 0 &&
        cusps.map((lon, i) => {
          const angle = lonToAngleDeg(lon, ascLon)
          const [x1, y1] = polarPoint(CX, CY, R_SIGN_INNER, angle)
          const [x2, y2] = polarPoint(CX, CY, R_CENTER, angle)
          const isAngular = i === 0 || i === 3 || i === 6 || i === 9
          return (
            <line
              key={i}
              x1={x1} y1={y1} x2={x2} y2={y2}
              className={isAngular ? 'stroke-primary' : undefined}
              stroke={isAngular ? undefined : 'currentColor'}
              strokeOpacity={isAngular ? 0.65 : 0.16}
              strokeWidth={isAngular ? 1.25 : 0.5}
            />
          )
        })}

      {/* ── House numbers ────────────────────────────────────────────────── */}
      {cusps.length > 0 &&
        cusps.map((lon, i) => {
          const nextLon = cusps[(i + 1) % cusps.length]
          const span = (nextLon - lon + 360) % 360
          const midLon = lon + span / 2
          const angle = lonToAngleDeg(midLon, ascLon)
          const [x, y] = polarPoint(CX, CY, R_HOUSE_NUM, angle)
          const isAngular = i === 0 || i === 3 || i === 6 || i === 9
          return (
            <text
              key={i}
              x={x} y={y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={isAngular ? 9.5 : 8.5}
              fill="currentColor"
              fillOpacity={isAngular ? 0.5 : 0.32}
              className="select-none"
            >
              {i + 1}
            </text>
          )
        })}

      {/* ── Planet position ticks ────────────────────────────────────────── */}
      {bodies.map((body, i) => {
        const angle = lonToAngleDeg(body.lon, ascLon)
        const [px1, py1] = polarPoint(CX, CY, R_PTICK_OUT, angle)
        const [px2, py2] = polarPoint(CX, CY, R_PTICK_IN, angle)
        return (
          <line
            key={i}
            x1={px1} y1={py1} x2={px2} y2={py2}
            stroke="currentColor"
            strokeOpacity={body.approximate ? 0.2 : 0.3}
            strokeWidth={0.75}
          />
        )
      })}

      {/* ── Body glyphs ──────────────────────────────────────────────────── */}
      {bodies.map((body, i) => {
        const angle = lonToAngleDeg(body.lon, ascLon)
        const r = bodyRadii[i] ?? R_BODY
        const [x, y] = polarPoint(CX, CY, r, angle)
        return (
          <text
            key={i}
            x={x} y={y}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize={13}
            className={cn(
              'select-none',
              body.approximate ? 'fill-amber-600 dark:fill-amber-400' : '',
            )}
            fill={body.approximate ? undefined : 'currentColor'}
            fillOpacity={body.approximate ? undefined : 0.88}
          >
            {body.symbol}
          </text>
        )
      })}

      {/* ── Inner circle ─────────────────────────────────────────────────── */}
      <circle
        cx={CX} cy={CY} r={R_CENTER}
        fill="none" stroke="currentColor" strokeOpacity={0.1} strokeWidth={0.5}
      />
    </svg>
  )
}
