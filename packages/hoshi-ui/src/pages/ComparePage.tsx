import { useState } from 'react'
import { useParams, Link } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { Loader2, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { WarningBanner } from '@/components/WarningBanner'
import { BodyTable } from '@/components/BodyTable'
import { AspectTable } from '@/components/AspectTable'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type CompareOutput, type CompositeOutput, type ZodiacMode, type HouseSystem } from '@/api/client'
import { chartDataFrom } from '@/lib/chartData'

type ViewMode = 'synastry' | 'composite'

interface FormState {
  chartBId: string
  mode: ZodiacMode
  houses: HouseSystem
}

type Result =
  | { view: 'synastry'; data: CompareOutput; chartBName: string }
  | { view: 'composite'; data: CompositeOutput; chartBName: string }

export function ComparePage() {
  const { id } = useParams<{ id: string }>()
  const { get, charts } = useChartStore()
  const chartA = id ? get(id) : undefined

  const otherCharts = charts.filter((c) => c.id !== id)

  const [viewMode, setViewMode] = useState<ViewMode>('synastry')
  const [form, setForm] = useState<FormState>({
    chartBId: otherCharts[0]?.id ?? '',
    mode: chartA?.input.mode ?? 'realsky',
    houses: chartA?.input.houses ?? 'porphyry',
  })
  const [result, setResult] = useState<Result | null>(null)

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }))

  const mutation = useMutation<Result, Error>({
    mutationFn: (): Promise<Result> => {
      if (!chartA) throw new Error('Chart not found')
      const chartB = get(form.chartBId)
      if (!chartB) throw new Error('Select a chart to compare against')
      if (viewMode === 'synastry') {
        return api.chartCompare({
          chartA: chartDataFrom(chartA.input),
          chartB: chartDataFrom(chartB.input),
          mode: form.mode,
          houses: form.houses,
          details: true,
          aspects: true,
        }).then((data): Result => ({ view: 'synastry', data, chartBName: chartB.name }))
      } else {
        return api.chartComposite({
          chartA: chartDataFrom(chartA.input),
          chartB: chartDataFrom(chartB.input),
          mode: form.mode,
          houses: form.houses,
          details: true,
          aspects: true,
        }).then((data): Result => ({ view: 'composite', data, chartBName: chartB.name }))
      }
    },
    onSuccess: (data) => setResult(data),
  })

  if (!chartA) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">Chart not found.</p>
        <Link to="/charts" className="text-xs text-primary hover:underline mt-2 inline-block">Back to charts</Link>
      </div>
    )
  }

  const synastryResult = result?.view === 'synastry' ? result.data : null
  const compositeResult = result?.view === 'composite' ? result.data : null
  const showHousesA = synastryResult?.bodiesA.some((b) => b.house != null) ?? false
  const showHousesB = synastryResult?.bodiesB.some((b) => b.house != null) ?? false
  const showCompositeHouses = compositeResult?.bodies.some((b) => b.house != null) ?? false

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-2 mb-8">
        <Link to={`/charts/${chartA.id}`} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Back to chart">
          <ArrowLeft size={16} />
        </Link>
        <h1 className="text-lg font-semibold">Compare — {chartA.name}</h1>
      </div>

      {/* View toggle */}
      <div className="flex gap-1 mb-6 p-1 bg-muted rounded-lg w-fit">
        {(['synastry', 'composite'] as ViewMode[]).map((v) => (
          <button
            key={v}
            onClick={() => setViewMode(v)}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors capitalize ${
              viewMode === v
                ? 'bg-background shadow-sm font-medium'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {v}
          </button>
        ))}
      </div>

      {/* Form */}
      <div className="space-y-5">
        {otherCharts.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No other saved charts to compare against.{' '}
            <Link to="/compute" className="text-primary hover:underline">Save another chart</Link> first.
          </p>
        ) : (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="chartB">Compare against</Label>
              <select id="chartB" value={form.chartBId} onChange={(e) => set({ chartBId: e.target.value })}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                {otherCharts.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="mode">Zodiac mode</Label>
                <select id="mode" value={form.mode} onChange={(e) => set({ mode: e.target.value as ZodiacMode })}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                  <option value="realsky">Real-sky</option>
                  <option value="tropical">Tropical</option>
                  <option value="vedic">Vedic</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="houses">House system</Label>
                <select id="houses" value={form.houses} onChange={(e) => set({ houses: e.target.value as HouseSystem })}
                  className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                  <option value="porphyry">Porphyry</option>
                  <option value="placidus">Placidus</option>
                  <option value="equal">Equal</option>
                  <option value="arc13">Arc-13</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              {mutation.isError && (
                <p className="text-sm text-destructive">
                  {mutation.error instanceof Error ? mutation.error.message : 'Something went wrong.'}
                </p>
              )}
              {!mutation.isError && <span />}
              <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.chartBId}>
                {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {mutation.isPending
                  ? 'Computing…'
                  : viewMode === 'synastry' ? 'Compare charts' : 'Compute composite'}
              </Button>
            </div>
          </>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-8 mt-10">
          <div className="h-px bg-border" />

          <WarningBanner warnings={result.data.warnings} />

          {result.view === 'synastry' && synastryResult && (
            <>
              <div className="text-xs text-muted-foreground space-x-3">
                <span>{chartA.name} · {synastryResult.header.dateA}</span>
                <span>vs</span>
                <span>{result.chartBName} · {synastryResult.header.dateB}</span>
                <span>·</span>
                <span className="capitalize">{synastryResult.header.mode}</span>
              </div>

              <section>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
                  {chartA.name}
                </p>
                <BodyTable bodies={synastryResult.bodiesA} showHouses={showHousesA} />
              </section>

              <section>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
                  {result.chartBName}
                </p>
                <BodyTable bodies={synastryResult.bodiesB} showHouses={showHousesB} />
              </section>

              {synastryResult.aspects?.length ? (
                <section>
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
                    Inter-aspects
                  </p>
                  <AspectTable
                    aspects={synastryResult.aspects}
                    chartLabels={{ a: chartA.name, b: result.chartBName }}
                  />
                </section>
              ) : null}
            </>
          )}

          {result.view === 'composite' && compositeResult && (
            <>
              <div className="text-xs text-muted-foreground space-x-3">
                <span>{chartA.name} · {compositeResult.header.dateA}</span>
                <span>×</span>
                <span>{result.chartBName} · {compositeResult.header.dateB}</span>
                <span>·</span>
                <span className="capitalize">{compositeResult.header.mode}</span>
                {compositeResult.header.houseSystem && (
                  <>
                    <span>·</span>
                    <span className="capitalize">{compositeResult.header.houseSystem}</span>
                  </>
                )}
              </div>

              <section>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
                  Composite chart
                </p>
                <BodyTable bodies={compositeResult.bodies} showHouses={showCompositeHouses} />
              </section>

              {compositeResult.aspects?.length ? (
                <section>
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
                    Aspects
                  </p>
                  <AspectTable aspects={compositeResult.aspects} />
                </section>
              ) : null}
            </>
          )}
        </div>
      )}
    </div>
  )
}
