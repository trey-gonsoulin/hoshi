import type { TallyOutput, TallyRow, ElementTally, ModalityTally } from '@/api/client'

const ELEMENT_ROWS: { label: string; key: keyof ElementTally }[] = [
  { label: 'Fire', key: 'fire' },
  { label: 'Earth', key: 'earth' },
  { label: 'Air', key: 'air' },
  { label: 'Water', key: 'water' },
]

const MODALITY_ROWS: { label: string; key: keyof ModalityTally }[] = [
  { label: 'Cardinal', key: 'cardinal' },
  { label: 'Fixed', key: 'fixed' },
  { label: 'Mutable', key: 'mutable' },
]

interface TallyDisplayProps {
  tallies: TallyOutput
}

function TallySection<T extends ElementTally | ModalityTally>({
  label,
  rows,
  data,
}: {
  label: string
  rows: { label: string; key: keyof T }[]
  data: T
}) {
  return (
    <section>
      <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2 select-none">
        {label}
      </p>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-border/40">
            <th className="pb-1.5 text-left font-normal text-muted-foreground text-xs min-w-[80px]">
              {label.slice(0, -1)}
            </th>
            <th className="pb-1.5 text-right font-normal text-muted-foreground text-xs w-16 tabular-nums">
              Planets
            </th>
            <th className="pb-1.5 text-right font-normal text-muted-foreground text-xs w-16 tabular-nums">
              All bodies
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ label: rowLabel, key }) => {
            const row = data[key] as TallyRow
            return (
              <tr key={rowLabel} className="border-b border-border/40 last:border-0">
                <td className="py-1.5 font-medium">{rowLabel}</td>
                <td className="py-1.5 tabular-nums text-right">{row.primary}</td>
                <td className="py-1.5 tabular-nums text-right text-muted-foreground">{row.total}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}

export function TallyDisplay({ tallies }: TallyDisplayProps) {
  return (
    <div className="grid grid-cols-2 gap-10 max-w-lg">
      <TallySection label="Elements" rows={ELEMENT_ROWS} data={tallies.elements} />
      <TallySection label="Modalities" rows={MODALITY_ROWS} data={tallies.modalities} />
    </div>
  )
}
