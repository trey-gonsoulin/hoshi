import { cn } from '@/lib/utils'
import { formatDeg, formatLon } from '@/lib/format'
import type { BodyEntry } from '@/api/client'

const GROUPS = [
  { label: 'Planets', kinds: ['Planet'] },
  { label: 'Angles', kinds: ['Angle'] },
  { label: 'Nodes & Points', kinds: ['Node', 'Point'] },
  { label: 'Lots', kinds: ['Lot'] },
]

interface BodyTableProps {
  bodies: BodyEntry[]
  showHouses: boolean
}

export function BodyTable({ bodies, showHouses }: BodyTableProps) {
  return (
    <div className="space-y-7">
      {GROUPS.map(({ label, kinds }) => {
        const group = bodies.filter((b) => kinds.includes(b.kind))
        if (!group.length) return null
        return (
          <section key={label}>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2 select-none">
              {label}
            </p>
            <table className="w-full text-sm border-collapse">
              <tbody>
                {group.map((body, i) => (
                  <tr key={i} className="border-b border-border/40 last:border-0">
                    {/* Glyph — the signature element */}
                    <td className="py-2 pr-3 w-6 text-base text-muted-foreground/70 select-none leading-none">
                      {body.symbol}
                    </td>
                    {/* Name */}
                    <td className="py-2 pr-5 font-medium min-w-[96px]">
                      {body.name}
                    </td>
                    {/* Sign — amber if uncertain */}
                    <td
                      className={cn(
                        'py-2 pr-5 min-w-[80px]',
                        body.approximate
                          ? 'text-amber-700 dark:text-amber-400'
                          : 'text-foreground',
                      )}
                    >
                      {body.sign}
                    </td>
                    {/* Degree within sign */}
                    <td
                      className={cn(
                        'py-2 pr-5 tabular-nums text-right w-[68px]',
                        body.approximate
                          ? 'text-amber-700 dark:text-amber-400'
                          : 'text-foreground',
                      )}
                    >
                      {formatDeg(body.degree)}
                    </td>
                    {/* Ecliptic longitude */}
                    <td className="py-2 pr-5 tabular-nums text-right w-[68px] text-muted-foreground">
                      {formatLon(body.lon)}
                    </td>
                    {/* Retrograde */}
                    <td className="py-2 pr-3 w-5 text-center text-rose-600 dark:text-rose-400 text-xs">
                      {body.rx ? '℞' : ''}
                    </td>
                    {/* House */}
                    {showHouses && (
                      <td className="py-2 pr-3 w-8 text-right tabular-nums text-muted-foreground text-xs">
                        {body.house != null ? `H${body.house}` : ''}
                      </td>
                    )}
                    {/* Dignity */}
                    <td className="py-2 w-5 text-center text-muted-foreground">
                      {body.dignity ?? ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )
      })}
    </div>
  )
}
