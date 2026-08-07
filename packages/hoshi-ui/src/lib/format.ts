import type { ChartOutput } from '@/api/client'

/** Format a within-sign degree float as "24°12'" */
export function formatDeg(deg: number): string {
  const d = Math.floor(deg)
  const m = Math.round((deg - d) * 60)
  return `${d}°${String(m).padStart(2, '0')}'`
}

/** Format an ecliptic longitude as "54.21°" */
export function formatLon(lon: number): string {
  return `${lon.toFixed(2)}°`
}

/** Render a ChartOutput as plain text suitable for pasting into an LLM. */
export function chartToText(result: ChartOutput): string {
  const { chart, bodies, aspects, cusps, tallies } = result
  const lines: string[] = []

  // Header
  lines.push(`# ${chart.name || 'Chart'}`)
  lines.push(`Date/time: ${chart.when}`)
  if (chart.lat != null && chart.lon != null) {
    lines.push(`Location: ${chart.lat.toFixed(4)}, ${chart.lon.toFixed(4)}`)
  }
  lines.push(`Zodiac mode: ${chart.mode}`)
  if (chart.houseSystem) lines.push(`House system: ${chart.houseSystem}`)
  lines.push('')

  // Bodies
  lines.push('## Placements')
  const hasHouses = bodies.some((b) => b.house != null)
  for (const b of bodies) {
    const parts = [`${b.name}: ${b.sign} ${formatDeg(b.degree)}`]
    if (b.rx) parts.push('(Rx)')
    if (hasHouses && b.house != null) parts.push(`House ${b.house}`)
    if (b.dignity) parts.push(`[${b.dignity}]`)
    lines.push(parts.join(' '))
  }

  // Aspects
  if (aspects?.length) {
    lines.push('')
    lines.push('## Aspects')
    for (const a of aspects) {
      const orb = `${a.orb.toFixed(1)}°`
      lines.push(`${a.bodyA} ${a.name} ${a.bodyB} (orb ${orb})`)
    }
  }

  // Cusps
  if (cusps.length) {
    lines.push('')
    lines.push('## House cusps')
    cusps.forEach((lon, i) => {
      lines.push(`House ${i + 1}: ${formatLon(lon)}`)
    })
  }

  // Tallies
  if (tallies) {
    lines.push('')
    lines.push('## Tallies')
    lines.push(
      'Elements: ' +
        (Object.entries(tallies.elements) as [string, { primary: number; total: number }][])
          .map(([k, v]) => `${k} ${v.primary}/${v.total}`)
          .join(', '),
    )
    lines.push(
      'Modalities: ' +
        (Object.entries(tallies.modalities) as [string, { primary: number; total: number }][])
          .map(([k, v]) => `${k} ${v.primary}/${v.total}`)
          .join(', '),
    )
  }

  return lines.join('\n')
}
