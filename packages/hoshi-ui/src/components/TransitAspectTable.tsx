import { lookupAspect, lookupBody } from '@/lib/astroInfo'
import { InfoTooltip } from '@/components/InfoTooltip'
import type { TransitAspect } from '@/api/client'

const KIND_ORDER = ['Major', 'Minor', 'Micro'] as const

const TIER_LABEL: Record<string, string> = {
  slow: 'Slow',
  medium: 'Medium',
  fast: 'Fast',
  luminary: 'Luminary',
}

const SENSITIVITY_CLASS: Record<string, string> = {
  primary: 'font-semibold',
  secondary: '',
  tertiary: 'text-muted-foreground',
}

function fmtDate(iso: string) {
  return iso.slice(0, 10)
}

interface TransitAspectTableProps {
  aspects: TransitAspect[]
  showWindows?: boolean
}

export function TransitAspectTable({ aspects, showWindows = false }: TransitAspectTableProps) {
  if (!aspects.length) {
    return <p className="text-sm text-muted-foreground">No transit aspects found.</p>
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
                {group.map((asp, i) => {
                  const sensClass = SENSITIVITY_CLASS[asp.natalSensitivity] ?? ''
                  const passLabel =
                    asp.passCount > 1 && asp.currentPass != null
                      ? `Pass ${asp.currentPass} of ${asp.passCount}`
                      : asp.passCount > 1
                        ? `${asp.passCount} passes`
                        : null
                  return (
                    <tr key={i} className="border-b border-border/40 last:border-0">
                      <td className={`py-2 pr-4 font-medium min-w-[90px] ${sensClass}`}>
                        <InfoTooltip info={lookupBody(asp.bodyA)}>{asp.bodyA}</InfoTooltip>
                      </td>
                      <td className="py-2 pr-4 w-6 text-center text-base leading-none">
                        {asp.symbol}
                      </td>
                      <td className={`py-2 pr-4 font-medium min-w-[90px] ${sensClass}`}>
                        <InfoTooltip info={lookupBody(asp.bodyB)}>{asp.bodyB}</InfoTooltip>
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground min-w-[96px]">
                        <InfoTooltip info={lookupAspect(asp.name)}>{asp.name}</InfoTooltip>
                      </td>
                      <td className="py-2 pr-4 tabular-nums text-right text-muted-foreground w-[56px]">
                        {asp.orb.toFixed(2)}°
                      </td>
                      {showWindows && (
                        <>
                          <td className="py-2 pr-4 text-muted-foreground text-xs w-[68px]">
                            {TIER_LABEL[asp.tier] ?? asp.tier}
                          </td>
                          <td className="py-2 text-xs text-muted-foreground">
                            {asp.passes.length > 1 ? (
                              <div className="flex flex-col gap-1">
                                {asp.passes.map((p, pi) => (
                                  <span key={pi}>
                                    <span className="text-primary/80 font-medium">
                                      {pi + 1}/{asp.passes.length}
                                    </span>
                                    {' '}
                                    {p.ingress ? fmtDate(p.ingress) : '…'}
                                    {' → '}
                                    <span className="text-foreground/80">{fmtDate(p.exact)}</span>
                                    {' → '}
                                    {p.egress ? fmtDate(p.egress) : '…'}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <div className="flex flex-col gap-0.5">
                                {(asp.ingress || asp.egress) && (
                                  <span>
                                    {asp.ingress ? fmtDate(asp.ingress) : '…'}
                                    {' – '}
                                    {asp.egress ? fmtDate(asp.egress) : '…'}
                                  </span>
                                )}
                                {asp.exact.length > 0 && (
                                  <span className="text-foreground/70">
                                    exact: {asp.exact.map(fmtDate).join(', ')}
                                  </span>
                                )}
                                {passLabel && (
                                  <span className="text-primary/80">{passLabel}</span>
                                )}
                              </div>
                            )}
                          </td>
                        </>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </section>
        )
      })}
    </div>
  )
}
