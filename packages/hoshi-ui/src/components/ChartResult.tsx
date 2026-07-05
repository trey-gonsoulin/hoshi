import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { WarningBanner } from '@/components/WarningBanner'
import { BodyTable } from '@/components/BodyTable'
import { AspectTable } from '@/components/AspectTable'
import { TallyDisplay } from '@/components/TallyDisplay'
import { ChartMeta } from '@/components/ChartMeta'
import { InfoTooltip } from '@/components/InfoTooltip'
import { WheelChart } from '@/components/WheelChart'
import { lookupHouse } from '@/lib/astroInfo'
import { formatLon } from '@/lib/format'
import type { ChartOutput } from '@/api/client'

interface ChartResultProps {
  result: ChartOutput
  actions?: React.ReactNode
}

export function ChartResult({ result, actions }: ChartResultProps) {
  const showHouses = result.bodies.some((b) => b.house != null)

  return (
    <div className="space-y-6">
      <div className="h-px bg-border" />

      <WarningBanner warnings={result.warnings} />

      <div className="flex items-start justify-between gap-4">
        <ChartMeta header={result.chart} />
        {actions && <div className="flex-shrink-0">{actions}</div>}
      </div>

      <WheelChart
        bodies={result.bodies}
        cusps={result.cusps}
        mode={result.chart.mode}
      />

      <Tabs defaultValue="bodies">
        <TabsList>
          <TabsTrigger value="bodies">Bodies</TabsTrigger>
          {result.aspects?.length ? (
            <TabsTrigger value="aspects">Aspects</TabsTrigger>
          ) : null}
          {result.tallies ? (
            <TabsTrigger value="tallies">Tallies</TabsTrigger>
          ) : null}
          {result.cusps.length ? (
            <TabsTrigger value="cusps">Cusps</TabsTrigger>
          ) : null}
        </TabsList>

        <TabsContent value="bodies" className="mt-6">
          <BodyTable bodies={result.bodies} showHouses={showHouses} />
        </TabsContent>

        {result.aspects?.length ? (
          <TabsContent value="aspects" className="mt-6">
            <AspectTable aspects={result.aspects} />
          </TabsContent>
        ) : null}

        {result.tallies ? (
          <TabsContent value="tallies" className="mt-6">
            <TallyDisplay tallies={result.tallies} />
          </TabsContent>
        ) : null}

        {result.cusps.length ? (
          <TabsContent value="cusps" className="mt-6">
            <CuspsTable cusps={result.cusps} />
          </TabsContent>
        ) : null}
      </Tabs>
    </div>
  )
}

function CuspsTable({ cusps }: { cusps: number[] }) {
  return (
    <table className="text-sm border-collapse">
      <tbody>
        {cusps.map((lon, i) => (
          <tr key={i} className="border-b border-border/40 last:border-0">
            <td className="py-1.5 pr-6 text-muted-foreground text-xs w-16">
              <InfoTooltip info={lookupHouse(i + 1)}>House {i + 1}</InfoTooltip>
            </td>
            <td className="py-1.5 tabular-nums">{formatLon(lon)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
