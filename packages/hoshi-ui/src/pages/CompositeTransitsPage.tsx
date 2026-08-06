import { useState } from 'react'
import { useParams, Link } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { Loader2, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { TimezonePicker } from '@/components/TimezonePicker'
import { WarningBanner } from '@/components/WarningBanner'
import { BodyTable } from '@/components/BodyTable'
import { AspectTable } from '@/components/AspectTable'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type TransitsOutput, type ZodiacMode, type HouseSystem } from '@/api/client'
import { chartDataFrom } from '@/lib/chartData'

const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone
const today = new Date().toISOString().slice(0, 10)

interface FormState {
  chartBId: string
  date: string
  time: string
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  showNatal: boolean
}

export function CompositeTransitsPage() {
  const { id } = useParams<{ id: string }>()
  const { get, charts } = useChartStore()
  const chartA = id ? get(id) : undefined

  const otherCharts = charts.filter((c) => c.id !== id)

  const [form, setForm] = useState<FormState>({
    chartBId: otherCharts[0]?.id ?? '',
    date: today,
    time: '',
    tz: localTz,
    mode: chartA?.input.mode ?? 'realsky',
    houses: chartA?.input.houses ?? 'porphyry',
    showNatal: false,
  })
  const [result, setResult] = useState<TransitsOutput | null>(null)
  const [chartBName, setChartBName] = useState<string>('')

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }))

  const mutation = useMutation({
    mutationFn: () => {
      if (!chartA) throw new Error('Chart not found')
      const chartB = get(form.chartBId)
      if (!chartB) throw new Error('Select a chart to composite with')
      return api.chartCompositeTransits({
        chartA: chartDataFrom(chartA.input),
        chartB: chartDataFrom(chartB.input),
        date: form.date || null,
        time: form.time || null,
        tz: form.tz || 'UTC',
        mode: form.mode,
        houses: form.houses,
        details: true,
        aspects: true,
        showNatal: form.showNatal,
        tier: 'all',
        sensitivity: '',
      })
    },
    onSuccess: (data) => {
      setChartBName(get(form.chartBId)?.name ?? '')
      setResult(data)
    },
  })

  if (!chartA) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">Chart not found.</p>
        <Link to="/charts" className="text-xs text-primary hover:underline mt-2 inline-block">Back to charts</Link>
      </div>
    )
  }

  const showHousesNatal = result?.natalBodies?.some((b) => b.house != null) ?? false

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-2 mb-8">
        <Link to={`/charts/${chartA.id}/composite`} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Back to composite">
          <ArrowLeft size={16} />
        </Link>
        <h1 className="text-lg font-semibold">Composite Transits — {chartA.name}</h1>
      </div>

      {/* Form */}
      <div className="space-y-5">
        {otherCharts.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No other saved charts to composite with.{' '}
            <Link to="/compute" className="text-primary hover:underline">Save another chart</Link> first.
          </p>
        ) : (
          <>
            <div className="space-y-1.5">
              <Label htmlFor="chartB">Composite with</Label>
              <select id="chartB" value={form.chartBId} onChange={(e) => set({ chartBId: e.target.value })}
                className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                {otherCharts.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="date">Transit date</Label>
                <Input id="date" type="date" value={form.date} onChange={(e) => set({ date: e.target.value })} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="time">Time <span className="text-muted-foreground font-normal">(optional)</span></Label>
                <Input
                  id="time"
                  type="text"
                  placeholder="HH:MM"
                  value={form.time}
                  onChange={(e) => set({ time: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="tz">Timezone</Label>
              <TimezonePicker id="tz" value={form.tz} onChange={(tz) => set({ tz })} />
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

            <label className="flex items-center gap-2.5 text-sm cursor-pointer select-none">
              <input type="checkbox" checked={form.showNatal} onChange={(e) => set({ showNatal: e.target.checked })}
                className="h-4 w-4 rounded border-input accent-primary" />
              Show composite bodies
            </label>

            <div className="flex items-center justify-between pt-1">
              {mutation.isError && (
                <p className="text-sm text-destructive">
                  {mutation.error instanceof Error ? mutation.error.message : 'Something went wrong.'}
                </p>
              )}
              {!mutation.isError && <span />}
              <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || !form.chartBId}>
                {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {mutation.isPending ? 'Computing…' : 'Compute transits'}
              </Button>
            </div>
          </>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-8 mt-10">
          <div className="h-px bg-border" />

          <WarningBanner warnings={result.warnings} />

          <div className="text-xs text-muted-foreground space-x-3">
            <span>Composite: {chartA.name} × {chartBName}</span>
            <span>·</span>
            <span>{result.header.transitWhen}</span>
            <span>·</span>
            <span className="capitalize">{result.header.mode}</span>
          </div>

          <section>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
              Transiting planets
            </p>
            <BodyTable bodies={result.transitBodies} showHouses={false} />
          </section>

          {result.natalBodies && (
            <section>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
                Composite bodies
              </p>
              <BodyTable bodies={result.natalBodies} showHouses={showHousesNatal} />
            </section>
          )}

          {result.aspects?.length ? (
            <section>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-4 select-none">
                Transit aspects
              </p>
              <AspectTable aspects={result.aspects} />
            </section>
          ) : null}
        </div>
      )}
    </div>
  )
}
