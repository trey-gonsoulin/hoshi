import { useState } from 'react'
import { useParams, Link } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { Loader2, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { TimezonePicker } from '@/components/TimezonePicker'
import { WarningBanner } from '@/components/WarningBanner'
import { TransitAspectTable } from '@/components/TransitAspectTable'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type ForecastOutput, type ZodiacMode, type HouseSystem, type ForecastRequest } from '@/api/client'
import { chartDataFrom } from '@/lib/chartData'

const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone
const today = new Date().toISOString().slice(0, 10)
const in90Days = new Date(Date.now() + 90 * 86400_000).toISOString().slice(0, 10)

interface FormState {
  fromDate: string
  toDate: string
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  tier: string
  sensitivity: string
}

export function ForecastPage() {
  const { id } = useParams<{ id: string }>()
  const { get } = useChartStore()
  const chart = id ? get(id) : undefined

  const [form, setForm] = useState<FormState>({
    fromDate: today,
    toDate: in90Days,
    tz: localTz,
    mode: chart?.input.mode ?? 'realsky',
    houses: chart?.input.houses ?? 'porphyry',
    tier: 'slow',
    sensitivity: '',
  })
  const [result, setResult] = useState<ForecastOutput | null>(null)

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }))

  const mutation = useMutation({
    mutationFn: () => {
      if (!chart) throw new Error('Chart not found')
      const req: ForecastRequest = {
        natal: chartDataFrom(chart.input),
        fromDate: form.fromDate || null,
        toDate: form.toDate || null,
        tz: form.tz || 'UTC',
        mode: form.mode,
        houses: form.houses,
        tier: form.tier,
        details: true,
        sensitivity: form.sensitivity,
      }
      return api.chartForecast(req)
    },
    onSuccess: setResult,
  })

  if (!chart) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">Chart not found.</p>
        <Link to="/charts" className="text-xs text-primary hover:underline mt-2 inline-block">Back to charts</Link>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center gap-2 mb-8">
        <Link to={`/charts/${chart.id}`} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Back to chart">
          <ArrowLeft size={16} />
        </Link>
        <h1 className="text-lg font-semibold">Forecast — {chart.name}</h1>
      </div>

      {/* Form */}
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="fromDate">From</Label>
            <Input id="fromDate" type="date" value={form.fromDate} onChange={(e) => set({ fromDate: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="toDate">To</Label>
            <Input id="toDate" type="date" value={form.toDate} onChange={(e) => set({ toDate: e.target.value })} />
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

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="tier">Planet tier</Label>
            <select id="tier" value={form.tier} onChange={(e) => set({ tier: e.target.value })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="slow">Slow (Jupiter+)</option>
              <option value="medium">Medium (Mars)</option>
              <option value="fast">Fast (Sun/Mercury/Venus)</option>
              <option value="luminary">Luminaries (Moon)</option>
              <option value="all">All planets</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="sensitivity">Natal sensitivity</Label>
            <select id="sensitivity" value={form.sensitivity} onChange={(e) => set({ sensitivity: e.target.value })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="">All points</option>
              <option value="primary">Primary (Sun/Moon/Asc/MC)</option>
              <option value="secondary">Secondary (personal planets)</option>
              <option value="tertiary">Tertiary (outer planets/nodes)</option>
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
          <Button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
            {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mutation.isPending ? 'Computing…' : 'Compute forecast'}
          </Button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-8 mt-10">
          <div className="h-px bg-border" />

          <WarningBanner warnings={result.warnings} />

          <div className="text-xs text-muted-foreground space-x-3">
            <span>Natal: {result.header.natalDate}</span>
            <span>·</span>
            <span>{result.header.fromDate} – {result.header.toDate}</span>
            <span>·</span>
            <span className="capitalize">{result.header.tier} planets</span>
            <span>·</span>
            <span className="capitalize">{result.header.mode}</span>
          </div>

          {result.aspects.length ? (
            <TransitAspectTable aspects={result.aspects} showWindows />
          ) : (
            <p className="text-sm text-muted-foreground">No transit aspects exact in this range.</p>
          )}
        </div>
      )}
    </div>
  )
}
