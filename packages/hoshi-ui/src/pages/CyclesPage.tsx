import { useState, useEffect, useRef } from 'react'
import { useParams, Link } from 'react-router'
import { useMutation } from '@tanstack/react-query'
import { Loader2, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useChartStore } from '@/hooks/useChartStore'
import { api, type CyclesOutput, type CycleEntry, type ZodiacMode, type HouseSystem, type CyclesRequest } from '@/api/client'
import { chartDataFrom } from '@/lib/chartData'

const today = new Date().toISOString().slice(0, 10)

interface FormState {
  fromDate: string
  mode: ZodiacMode
  houses: HouseSystem
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
    })
  } catch {
    return iso
  }
}

function CycleRow({ entry }: { entry: CycleEntry }) {
  const unavailable = !entry.available
  const approximate = entry.note?.startsWith('Approximate')

  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-3 pr-4 font-medium text-sm">
        {entry.natalSignSymbol ? (
          <span title={entry.bodyName}>{entry.bodyName}</span>
        ) : entry.bodyName}
      </td>
      <td className="py-3 pr-4 text-sm text-muted-foreground">
        {entry.natalSign}
        {entry.natalSignSymbol && (
          <span className="ml-1 opacity-60">{entry.natalSignSymbol}</span>
        )}
        {' '}
        <span className="text-xs opacity-50">{entry.natalLon.toFixed(2)}°</span>
      </td>
      <td className="py-3 pr-4 text-sm text-muted-foreground">
        {entry.periodLabel}
      </td>
      <td className="py-3 pr-4 text-sm">
        {unavailable ? (
          <span className="text-muted-foreground italic text-xs">unavailable</span>
        ) : (
          <div className="space-y-0.5">
            {entry.exact.map((iso, i) => (
              <div key={i} className={approximate ? 'text-muted-foreground' : ''}>
                {approximate && <span className="mr-1 opacity-50">~</span>}
                {formatDate(iso)}
              </div>
            ))}
          </div>
        )}
      </td>
      <td className="py-3 text-sm text-muted-foreground">
        {unavailable ? '—' : entry.passCount}
      </td>
      {entry.note && (
        <td className="py-3 pl-4 text-xs text-muted-foreground max-w-xs">
          {entry.note}
        </td>
      )}
    </tr>
  )
}

export function CyclesPage() {
  const { id } = useParams<{ id: string }>()
  const { get } = useChartStore()
  const chart = id ? get(id) : undefined

  const [form, setForm] = useState<FormState>({
    fromDate: today,
    mode: chart?.input.mode ?? 'realsky',
    houses: chart?.input.houses ?? 'porphyry',
  })
  const [result, setResult] = useState<CyclesOutput | null>(null)

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }))

  const mutation = useMutation({
    mutationFn: () => {
      if (!chart) throw new Error('Chart not found')
      const req: CyclesRequest = {
        natal: chartDataFrom(chart.input),
        fromDate: form.fromDate || null,
        tz: 'UTC',
        mode: form.mode,
        houses: form.houses,
      }
      return api.chartCycles(req)
    },
    onSuccess: setResult,
  })

  const didAutorun = useRef(false)
  useEffect(() => {
    if (!didAutorun.current && chart) {
      didAutorun.current = true
      mutation.mutate()
    }
  }, []) // intentional: one-shot on mount

  if (!chart) {
    return (
      <div className="max-w-2xl mx-auto px-6 py-16 text-center">
        <p className="text-muted-foreground text-sm">Chart not found.</p>
        <Link to="/charts" className="text-xs text-primary hover:underline mt-2 inline-block">Back to charts</Link>
      </div>
    )
  }

  const hasNotes = result?.cycles.some((e) => e.note)

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      <div className="flex items-center gap-2 mb-8">
        <Link to={`/charts/${chart.id}`} className="text-muted-foreground hover:text-foreground transition-colors" aria-label="Back to chart">
          <ArrowLeft size={16} />
        </Link>
        <h1 className="text-lg font-semibold">Cycles — {chart.name}</h1>
      </div>

      {/* Form */}
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="fromDate">From date</Label>
            <Input id="fromDate" type="date" value={form.fromDate} onChange={(e) => set({ fromDate: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="mode">Zodiac mode</Label>
            <select id="mode" value={form.mode} onChange={(e) => set({ mode: e.target.value as ZodiacMode })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
              <option value="realsky">Real-sky</option>
              <option value="tropical">Tropical</option>
              <option value="vedic">Vedic</option>
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
            {mutation.isPending ? 'Computing…' : 'Compute cycles'}
          </Button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6 mt-10">
          <div className="h-px bg-border" />

          <div className="text-xs text-muted-foreground space-x-3">
            <span>Natal: {result.natalDate}</span>
            <span>·</span>
            <span>From: {result.fromDate}</span>
            <span>·</span>
            <span className="capitalize">{result.mode}</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border">
                  <th className="pb-2 pr-4 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Body</th>
                  <th className="pb-2 pr-4 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Natal position</th>
                  <th className="pb-2 pr-4 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Period</th>
                  <th className="pb-2 pr-4 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Next return</th>
                  <th className="pb-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Passes</th>
                  {hasNotes && <th className="pb-2 pl-4 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Note</th>}
                </tr>
              </thead>
              <tbody>
                {result.cycles.map((entry) => (
                  <CycleRow key={entry.bodyPid} entry={entry} />
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-muted-foreground">
            ~ Approximate dates for bodies beyond the DE421 ephemeris range (2053).
          </p>
        </div>
      )}
    </div>
  )
}
