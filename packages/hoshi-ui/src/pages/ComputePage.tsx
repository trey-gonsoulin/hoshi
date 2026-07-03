import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { WarningBanner } from '@/components/WarningBanner'
import { BodyTable } from '@/components/BodyTable'
import { AspectTable } from '@/components/AspectTable'
import { TallyDisplay } from '@/components/TallyDisplay'
import { ChartMeta } from '@/components/ChartMeta'
import { formatLon } from '@/lib/format'
import { api, type ChartOutput, type ZodiacMode, type HouseSystem } from '@/api/client'

interface FormState {
  date: string
  time: string
  useCoords: boolean
  location: string
  lat: string
  lon: string
  tz: string
  mode: ZodiacMode
  houses: HouseSystem
  details: boolean
  aspects: boolean
}

const localTz = Intl.DateTimeFormat().resolvedOptions().timeZone

const defaultForm: FormState = {
  date: '',
  time: '',
  useCoords: false,
  location: '',
  lat: '',
  lon: '',
  tz: localTz,
  mode: 'realsky',
  houses: 'porphyry',
  details: false,
  aspects: false,
}

function buildRequest(f: FormState) {
  const base = {
    date: f.date,
    time: f.time || undefined,
    tz: f.tz || 'UTC',
    mode: f.mode,
    houses: f.houses,
    details: f.details,
    aspects: f.aspects,
    cusps: false,
  }
  if (f.useCoords) {
    return {
      ...base,
      lat: f.lat ? parseFloat(f.lat) : undefined,
      lon: f.lon ? parseFloat(f.lon) : undefined,
    }
  }
  return { ...base, location: f.location || undefined }
}

export function ComputePage() {
  const [form, setForm] = useState<FormState>(defaultForm)
  const [result, setResult] = useState<ChartOutput | null>(null)

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }))

  const mutation = useMutation({
    mutationFn: () => api.computeChart(buildRequest(form)),
    onSuccess: (data) => setResult(data),
  })

  const showHouses =
    result != null &&
    result.bodies.some((b) => b.house != null)

  return (
    <div className="max-w-2xl mx-auto px-6 py-10 space-y-10">

      {/* Input form */}
      <div className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="date">Date</Label>
            <Input
              id="date"
              type="date"
              required
              value={form.date}
              onChange={(e) => set({ date: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="time">
              Time{' '}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <Input
              id="time"
              type="time"
              value={form.time}
              onChange={(e) => set({ time: e.target.value })}
            />
          </div>
        </div>

        {!form.useCoords ? (
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <Label htmlFor="location">Location</Label>
              <button
                type="button"
                className="text-xs text-primary hover:underline"
                onClick={() => set({ useCoords: true })}
              >
                Use coordinates instead
              </button>
            </div>
            <Input
              id="location"
              placeholder="e.g. New York, NY"
              value={form.location}
              onChange={(e) => set({ location: e.target.value })}
            />
          </div>
        ) : (
          <div className="space-y-1.5">
            <div className="flex items-baseline justify-between">
              <Label>Coordinates</Label>
              <button
                type="button"
                className="text-xs text-primary hover:underline"
                onClick={() => set({ useCoords: false })}
              >
                Use location name instead
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Input
                placeholder="Latitude (e.g. 40.7128)"
                type="number"
                step="any"
                value={form.lat}
                onChange={(e) => set({ lat: e.target.value })}
              />
              <Input
                placeholder="Longitude (e.g. -74.006)"
                type="number"
                step="any"
                value={form.lon}
                onChange={(e) => set({ lon: e.target.value })}
              />
            </div>
          </div>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="tz">Timezone</Label>
          <Input
            id="tz"
            placeholder="e.g. America/New_York"
            value={form.tz}
            onChange={(e) => set({ tz: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="mode">Zodiac mode</Label>
            <select
              id="mode"
              value={form.mode}
              onChange={(e) => set({ mode: e.target.value as ZodiacMode })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="realsky">Real-sky</option>
              <option value="tropical">Tropical</option>
              <option value="vedic">Vedic</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="houses">House system</Label>
            <select
              id="houses"
              value={form.houses}
              onChange={(e) => set({ houses: e.target.value as HouseSystem })}
              className="w-full h-9 rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value="porphyry">Porphyry</option>
              <option value="placidus">Placidus</option>
              <option value="equal">Equal</option>
              <option value="arc13">Arc-13</option>
            </select>
          </div>
        </div>

        <label className="flex items-center gap-2.5 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            checked={form.details}
            onChange={(e) => set({ details: e.target.checked, aspects: e.target.checked ? form.aspects : false })}
            className="h-4 w-4 rounded border-input accent-primary"
          />
          Include minor bodies, nodes, and lots
        </label>

        {form.details && (
          <label className="flex items-center gap-2.5 text-sm cursor-pointer select-none ml-6">
            <input
              type="checkbox"
              checked={form.aspects}
              onChange={(e) => set({ aspects: e.target.checked })}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            Include aspects
          </label>
        )}

        <div className="flex items-center justify-between pt-1">
          {mutation.isError && (
            <p className="text-sm text-destructive">
              {mutation.error instanceof Error
                ? mutation.error.message
                : 'Something went wrong.'}
            </p>
          )}
          {!mutation.isError && <span />}
          <Button
            onClick={() => mutation.mutate()}
            disabled={!form.date || mutation.isPending}
          >
            {mutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {mutation.isPending ? 'Computing…' : 'Compute chart'}
          </Button>
        </div>
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-6">
          <div className="h-px bg-border" />

          <WarningBanner warnings={result.warnings} />

          <ChartMeta header={result.chart} />

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
                <CuspsTab cusps={result.cusps} />
              </TabsContent>
            ) : null}
          </Tabs>
        </div>
      )}
    </div>
  )
}

function CuspsTab({ cusps }: { cusps: number[] }) {
  return (
    <table className="text-sm border-collapse">
      <tbody>
        {cusps.map((lon, i) => (
          <tr key={i} className="border-b border-border/40 last:border-0">
            <td className="py-1.5 pr-6 text-muted-foreground text-xs w-16">
              House {i + 1}
            </td>
            <td className="py-1.5 tabular-nums">{formatLon(lon)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
