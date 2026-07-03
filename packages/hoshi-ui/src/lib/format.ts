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
