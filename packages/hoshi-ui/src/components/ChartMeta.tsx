import type { ChartHeader } from '@/api/client'

const MODE_LABELS: Record<string, string> = {
  realsky: 'Real-sky',
  tropical: 'Tropical',
  vedic: 'Vedic',
}

const HOUSE_LABELS: Record<string, string> = {
  porphyry: 'Porphyry',
  placidus: 'Placidus',
  equal: 'Equal',
  arc13: 'Arc-13',
}

export function ChartMeta({ header }: { header: ChartHeader }) {
  const parts: string[] = []
  if (header.when) parts.push(header.when)
  if (header.mode) parts.push(MODE_LABELS[header.mode] ?? header.mode)
  if (header.houseSystem)
    parts.push(HOUSE_LABELS[header.houseSystem] ?? header.houseSystem)
  if (header.lat != null && header.lon != null)
    parts.push(`${header.lat.toFixed(2)}°, ${header.lon.toFixed(2)}°`)

  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
      {header.name && (
        <span className="text-base font-semibold">{header.name}</span>
      )}
      {parts.map((p, i) => (
        <span key={i} className="text-sm text-muted-foreground">
          {p}
        </span>
      ))}
    </div>
  )
}
