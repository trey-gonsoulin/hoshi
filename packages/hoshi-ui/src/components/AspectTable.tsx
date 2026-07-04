import { lookupAspect, lookupBody } from '@/lib/astroInfo'
import { InfoTooltip } from '@/components/InfoTooltip'
import type { Aspect } from '@/api/client'

const KIND_ORDER = ['Major', 'Minor', 'Micro'] as const

interface AspectTableProps {
  aspects: Aspect[]
}

export function AspectTable({ aspects }: AspectTableProps) {
  if (!aspects.length) {
    return <p className="text-sm text-muted-foreground">No aspects found.</p>
  }

  const byKind = Object.fromEntries(
    KIND_ORDER.map((k) => [k, aspects.filter((a) => a.kind === k)]),
  )

  return (
    <div className="space-y-7">
      {KIND_ORDER.map((kind) => {
        const group = byKind[kind]
        if (!group?.length) return null
        return (
          <section key={kind}>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2 select-none">
              {kind} Aspects
            </p>
            <table className="w-full text-sm border-collapse">
              <tbody>
                {group.map((asp, i) => (
                  <tr key={i} className="border-b border-border/40 last:border-0">
                    {/* Body A */}
                    <td className="py-2 pr-4 font-medium min-w-[90px]">
                      <InfoTooltip info={lookupBody(asp.body_a)}>
                        {asp.body_a}
                      </InfoTooltip>
                    </td>
                    {/* Aspect symbol */}
                    <td className="py-2 pr-4 w-6 text-center text-base leading-none">
                      {asp.symbol}
                    </td>
                    {/* Body B */}
                    <td className="py-2 pr-5 font-medium min-w-[90px]">
                      <InfoTooltip info={lookupBody(asp.body_b)}>
                        {asp.body_b}
                      </InfoTooltip>
                    </td>
                    {/* Aspect name */}
                    <td className="py-2 pr-5 text-muted-foreground min-w-[96px]">
                      <InfoTooltip info={lookupAspect(asp.name)}>
                        {asp.name}
                      </InfoTooltip>
                    </td>
                    {/* Orb */}
                    <td className="py-2 tabular-nums text-right text-muted-foreground w-[56px]">
                      {asp.orb.toFixed(2)}°
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
