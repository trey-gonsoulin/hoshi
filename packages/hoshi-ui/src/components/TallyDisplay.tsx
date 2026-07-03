import type { TallyOutput } from '@/api/client'

const ELEMENTS = ['Fire', 'Earth', 'Air', 'Water'] as const
const MODALITIES = ['Cardinal', 'Fixed', 'Mutable'] as const

interface TallyDisplayProps {
  tallies: TallyOutput
}

function TallySection({
  label,
  keys,
  data,
}: {
  label: string
  keys: readonly string[]
  data: TallyOutput['elements'] | TallyOutput['modalities']
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
          {keys.map((key) => {
            const row = data[key]
            return (
              <tr key={key} className="border-b border-border/40 last:border-0">
                <td className="py-1.5 font-medium">{key}</td>
                <td className="py-1.5 tabular-nums text-right">
                  {row?.primary ?? 0}
                </td>
                <td className="py-1.5 tabular-nums text-right text-muted-foreground">
                  {row?.total ?? 0}
                </td>
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
      <TallySection label="Elements" keys={ELEMENTS} data={tallies.elements} />
      <TallySection
        label="Modalities"
        keys={MODALITIES}
        data={tallies.modalities}
      />
    </div>
  )
}
